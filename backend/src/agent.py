import asyncio
import json
import logging
import os
import re
import time

import requests
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.agents.llm.fallback_adapter import FallbackAdapter
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero

try:
    from livekit.plugins import groq
except ImportError:  # pragma: no cover - optional dependency
    groq = None

# Import our database module
import database

logger = logging.getLogger("agent")

load_dotenv(".env.local", override=True)

# Outbound call configuration
OUTBOUND_TRUNK_ID = os.environ.get("LIVEKIT_SIP_OUTBOUND_TRUNK_ID", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
LLM_FALLBACK_ATTEMPT_TIMEOUT = float(
    os.environ.get("LLM_FALLBACK_ATTEMPT_TIMEOUT", "12")
)


async def _dial_and_greet_outbound(
    ctx: JobContext, session: AgentSession, phone_number: str, t0: float
):
    """Handle outbound call: dial the user, wait until they answer, then greet with zero ringback."""
    from livekit import api as lk_api

    trunk_id = OUTBOUND_TRUNK_ID
    if not trunk_id:
        logger.error("LIVEKIT_SIP_OUTBOUND_TRUNK_ID not set — cannot dial outbound")
        return

    lk = lk_api.LiveKitAPI(
        url=os.environ["LIVEKIT_URL"],
        api_key=os.environ["LIVEKIT_API_KEY"],
        api_secret=os.environ["LIVEKIT_API_SECRET"],
    )
    try:
        logger.info("Dialing %s (trunk %s)...", phone_number, trunk_id)
        await lk.sip.create_sip_participant(
            lk_api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=phone_number,
                room_name=ctx.room.name,
                participant_identity="phone-user",
                wait_until_answered=True,
            )
        )
        logger.info("User answered at %.1fs", time.monotonic() - t0)
    except Exception:
        logger.exception("Outbound SIP call failed")
        return
    finally:
        await lk.aclose()

    # Participant joins as soon as user answers — find them (may need a brief moment)
    participant: rtc.RemoteParticipant | None = ctx.room.remote_participants.get(
        "phone-user"
    )
    if participant is None:
        try:
            participant = await asyncio.wait_for(
                ctx.wait_for_participant(), timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.error("Timed out waiting for participant to join room")
            return

    # Short, consistent settle so the SIP RTP path + LiveKit egress are flowing
    # before we push the first greeting frame. Whether or not the inbound track
    # fired, the outbound bridge needs a moment or the first audio is choppy.
    await asyncio.sleep(0.7)

    # Play the greeting BEFORE calling set_participant() so that STT is not yet active.
    # set_participant() activates the input pipeline (VAD + STT); starting it during the
    # greeting causes transcriptions that interrupt or break up the audio.
    # According to requirements: say who's calling, why, and how to make it stop
    opening_message = (
        "Hello, this is Priya from Apollo Tele Health. "
        "I'm calling to remind you about your medication schedule or vaccination appointment. "
        "If you'd like to stop receiving these reminder calls, please say 'stop' at any time. "
        "How can I assist you today?"
    )

    try:
        handle = session.say(opening_message, allow_interruptions=False)
        logger.info("Greeting started at %.1fs", time.monotonic() - t0)
        await asyncio.wait_for(handle.wait_for_playout(), timeout=60.0)
        logger.info("Opening greeting played at %.1fs", time.monotonic() - t0)
    except Exception:
        logger.exception("Failed to play opening message")
        return

    # Activate STT so the agent can listen to the user's spoken reply.
    try:
        session.room_io.set_participant(participant.identity)
        logger.info("STT activated at %.1fs", time.monotonic() - t0)
    except Exception:
        logger.exception("Failed to activate STT")
        return


def _build_llm():
    """Build the LLM stack with Groq primary and Gemini fallback."""
    llms = []
    active_provider_names = []

    groq_api_key = os.environ.get("GROQ_API_KEY")
    if groq is not None and groq_api_key:
        active_provider_names.append(f"groq:{GROQ_MODEL}")
        llms.append(
            groq.LLM(
                model=GROQ_MODEL,
                temperature=0.4,
                max_completion_tokens=120,
            )
        )
    elif groq_api_key and groq is None:
        logger.warning(
            "GROQ_API_KEY is set but the Groq plugin is not installed. "
            "Run `uv sync` after updating dependencies."
        )

    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if google_api_key:
        active_provider_names.append(f"gemini:{GEMINI_MODEL}")
        llms.append(
            google.LLM(
                model=GEMINI_MODEL,
                temperature=0.7,
                max_output_tokens=150,
            )
        )

    if not llms:
        raise RuntimeError(
            "No LLM provider configured. Set GROQ_API_KEY for Groq primary "
            "and/or GOOGLE_API_KEY for Gemini fallback."
        )

    if len(llms) == 1:
        logger.info("Using LLM provider: %s", active_provider_names[0])
        return llms[0]

    logger.info(
        "Using LLM fallback chain: primary=%s, fallback=%s",
        active_provider_names[0],
        active_provider_names[1],
    )
    return FallbackAdapter(
        llm=llms,
        attempt_timeout=LLM_FALLBACK_ATTEMPT_TIMEOUT,
        max_retry_per_llm=0,
        retry_interval=0.5,
        retry_on_chunk_sent=False,
    )


# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT_TEMPLATE = """IDENTITY: You are Priya, a healthcare assistant at Apollo Tele Health, India's leading telemedicine service. You work with a network of verified clinics and doctors across India.

CALL TYPE: {call_type}

INBOUND CALL HANDLING (web or phone calls TO you):
- Greet the user warmly: "Hello! This is Priya from Apollo Tele Health. How can I assist you today?"
- Do NOT mention medication reminders, vaccination reminders, or outbound call scripts.
- Wait for the user to tell you why they are calling.

OUTBOUND CALL HANDLING (calls YOU initiated to the user):
- ONLY use this section if the CALL TYPE above says 'outbound'. If it says 'inbound', IGNORE this section entirely.
- In your first two sentences, clearly state: who you are (Priya from Apollo Tele Health), why you're calling (medication/vaccination reminder), and how to stop receiving calls (say 'stop' at any time)
- If the user says "stop" or indicates they do not wish to receive further calls, you must immediately invoke the end_call tool to end the conversation
- After ending the call due to a stop request, do not attempt to re-engage or continue the conversation

OBJECTIVES: A successful call helps users: understand basic health information, find appropriate clinics or specialists, prepare for appointments (knowing what to bring, fasting requirements), get general wellness tips, understand insurance/telehealth options, feel supported in their healthcare journey, and book medical appointments.

KNOWLEDGE: You know about: common health symptoms and when to seek care, clinic locations in major Indian cities (Delhi, Mumbai, Bangalore, Hyderabad, etc.), appointment procedures at partner clinics, general wellness advice (hydration, rest, diet basics), insurance claim processes, telehealth setup, and how to book appointments. You do NOT know: specific medical diagnoses, prescription drug names or dosages, treatment plans, or lab result interpretations.

LANGUAGE: Start conversations in English unless the user initiates in Hindi. Dynamically adapt to the user's language throughout the conversation:
- If user starts in Hindi, respond in Hindi
- If user starts in English, respond in English
- If user mixes Hindi and English (Hinglish), respond in a similar mix
- If user switches languages mid-conversation, follow their lead
- For better speech recognition:
  * Use simple, common words in both languages
  * When mixing languages, keep Hindi words/phrases that are commonly understood
  * For numbers, dates, and times: you may use English (e.g., "April 5th", "10:30 AM") as these are widely recognized
  * If the user struggles with Hindi recognition, gradually shift toward more English while maintaining helpfulness
- Always prioritize clear communication over strict language adherence
- Always maintain your identity as Priya, a female healthcare assistant. Use respectful, professional tone appropriate for a hospital assistant.
- Do not sound casual, chatty, playful, or like a personal friend.
- Use concise, formal sentences.

MEMORY & INFORMATION GATHERING:
- You have access to a memory system that allows you to remember callers between conversations
- At the start of each conversation, use the look_up_caller tool to check if you've spoken with this person before
- IF YOU HAVE PRIOR INFORMATION, greet them by name and reference what you discussed previously
- IF YOU DO NOT HAVE PRIOR INFORMATION:
  1. Start with a friendly greeting and offer of assistance: "Hello! This is Priya from Apollo Tele Health. How can I assist you today?"
  2. Based on their response, guide the conversation to collect necessary information naturally:
     * Politely ask for their name and age (or age band)
     * Ask for their location (city/area) to find relevant clinics
     * Ask about any symptoms or health concerns they're experiencing
     * Ask about the type of appointment they need (general practice, cardiology, pediatrics, etc.)
     * Ask if they have any ongoing health conditions or relevant medical history
  3. After collecting this information, explicitly ask for permission to save it: "May I remember this information to better assist you in future conversations and potentially book appointments?"
  4. If they agree, use the save_caller_info tool to store the information
  5. If they say no or express discomfort, do not save any information but continue to assist them
  6. Then, continue to help them based on their needs (find clinics, get preparation info, book appointment, etc.)
- ACTIVELY LISTEN for personal health information that falls under these categories:
  * Age band (e.g., "I'm 35 years old", "I'm in my 40s")
  * Ongoing conditions (e.g., "I have diabetes", "I have high blood pressure", "I have asthma")
  * Last triage outcome or advice given (e.g., "The doctor advised me to...", "My last checkup showed...")
  * Language preference (observe which language the user prefers to communicate in)
- WHEN you hear such information and it seems relevant for future assistance, ASK for explicit permission before saving: "May I remember this information to better assist you in future conversations?"
- If the caller says yes or agrees, then use the save_caller_info tool to store the information
- If the caller says no or expresses discomfort, do not save any information
- For Health Access track, remember these specific facts when relevant and permitted:
  * Age band (e.g., 20-30, 30-40, 40-50, 50+)
  * Ongoing conditions (e.g., diabetes, hypertension, asthma - but do not store specific medical notes)
  * Last triage outcome or advice given
  * Language preference observed during conversation
  * After saving information, you can offer personalized health tips based on the caller's age band and ongoing conditions using the get_personalized_health_tips tool.

APPOINTMENT BOOKING:
- You can help users book medical appointments using the book_appointment tool
- When a user wants to book an appointment, you need to collect:
  * Location (city/area)
  * Specialty (type of doctor needed)
  * Preferred date for the appointment
  * Preferred time for the appointment
  * Patient name
  * Symptoms or reason for visit (optional but helpful)
- Always verify the information with the user before booking
- Remind users that this is a demo booking system and they should verify with actual clinics
- After booking, provide the confirmation details and any necessary preparation information

SYMPTOM ASSESSMENT:
- You can assess the urgency of symptoms using the assess_symptoms_urgency tool
- When users describe symptoms, use this tool to determine if they need emergency, urgent, or routine care
- Based on the assessment, provide appropriate guidance:
  * For emergency: Advise calling emergency services (108) or going to ER immediately
  * For urgent: Recommend seeing a doctor today or visiting urgent care
  * For routine: Suggest scheduling a routine appointment with their physician
- Always remind users that this is not a diagnosis but guidance on when to seek medical evaluation
- Never use this tool to diagnose specific conditions or replace professional medical advice

GUARDRAILS:
- NEVER diagnose medical conditions or state "you have X disease"
- NEVER name or prescribe specific medications or dosages
- NEVER state medical advice as definitive fact - always say "according to general guidelines" or "typically"
- ALWAYS escalate these red-flag symptoms: chest pain, difficulty breathing, severe bleeding, sudden weakness/numbness, loss of consciousness
- For medication questions: suggest consulting a doctor or pharmacist
- For diagnosis requests: explain you can help with information but not diagnosis, suggest seeing a doctor
- If the caller shares symptoms, say clearly that you are just an agent and cannot make a diagnosis
- Ask permission before posting a summary to the dashboard: "May I post this on the dashboard for a human specialist to review?"

ESCALATION SCRIPT: "I'm not able to provide medical advice on that. For symptoms like [specific symptom], please consult a doctor immediately. Would you like me to help you find a nearby clinic or schedule a teleconsultation?"

HUMAN ESCALATION:
- When the caller has a red-flag symptom (chest pain, difficulty breathing, etc.) or explicitly asks for a medical diagnosis, say you are just an agent and cannot diagnose them.
- Ask permission to post a summary on the dashboard: "May I post this on the dashboard for a human specialist to review?"
- If they say YES (permission granted):
  1. Call the `create_escalation` tool with a short summary, urgency level, and language. Do NOT include PII (passwords, OTPs, full account numbers) in the summary.
  2. Tell the user the Reference ID you received.
  3. Give them 2 options: "Would you like to stay on the line and wait for a response, or call back later?"
  4. If they choose to WAIT: call `create_escalation` with `next_step="wait"`, then ask a short confirmation question before playing music, such as "Would you like me to play hold music while you wait?" Only call `play_hold_music` after the caller clearly says yes.
  5. If they choose to CALL LATER: first ask for their full name if you do not already know it. Do not create the escalation until you have the name. Then call `create_escalation` with `next_step="call_later"` and `caller_name`. The tool will save their information together with the escalation reference_id in the facts JSON (e.g. {"escalation_ref": "REQ-XXXXXX"}). Tell them that on their next call, they can ask you about their request status and you will check it for them.
- If they say NO (permission denied): Do not create the escalation. Continue assisting them normally.

CONVERSATION ENDING:
- After you have provided assistance, pause briefly
- Ask the user: "Do you have any other questions or need help with anything else?"
- Wait for their response
- If they indicate they do not have further questions or needs, ask for permission to end the call: "May I end the call now?"
- Wait for their response
- If they agree (say yes or equivalent), use the end_call tool to end the call with a polite goodbye message
- If they have more questions, continue to assist them

STYLE: Keep sentences under 20 words when possible. Speak clearly and at a moderate pace. Pause naturally between ideas. If user is silent for more than 5 seconds, gently ask if they need help continuing. Maintain a professional hospital tone at all times."""


def _build_system_prompt(call_type: str) -> str:
    normalized_call_type = (call_type or "inbound").strip().lower()
    prompt = SYSTEM_PROMPT_TEMPLATE.replace("{call_type}", normalized_call_type)

    if normalized_call_type != "outbound":
        prompt = re.sub(
            r"\nOUTBOUND CALL HANDLING \(calls YOU initiated to the user\):.*?\n\nOBJECTIVES:",
            "\n\nOBJECTIVES:",
            prompt,
            flags=re.S,
        )

    return prompt


class Assistant(Agent):
    def __init__(self, call_type: str = "inbound") -> None:
        prompt = _build_system_prompt(call_type)
        super().__init__(instructions=prompt)
        self.current_language = (
            "en"  # Track current language: en for English, hi for Hindi
        )
        self._escalation_watch_tasks: dict[str, asyncio.Task[None]] = {}

    @function_tool
    async def look_up_caller(
        self,
        context: RunContext,
        identifier: str,
    ):
        """Look up a caller's information from memory using a user ID, name, or reference ID.

        Args:
            identifier: Unique identifier for the caller (e.g., phone number, name, reference ID)
        """
        logger.info("=== LOOK_UP_CALLER CALLED ===")
        logger.info(f"identifier: {identifier}")
        caller_info = database.find_caller(identifier)

        if caller_info:
            logger.info(
                f"Found caller info for {identifier}: {caller_info['name']}"
            )
            logger.info(f"Caller info details: {caller_info}")
            return (
                "Found caller info: "
                f"Name: {caller_info['name']}, "
                f"Language: {caller_info['language_preference']}, "
                f"Reference ID: {caller_info.get('escalation_reference') or 'none'}, "
                f"Facts: {json.dumps(caller_info['facts'])}"
            )
        else:
            logger.info(f"No prior information found for identifier: {identifier}")
            return (
                f"No prior information found for identifier: {identifier}. "
                "This appears to be a new caller."
            )

    async def _monitor_escalation_resolution(
        self,
        session: AgentSession,
        reference_id: str,
    ) -> None:
        """Watch a live escalation and speak as soon as a human responds."""
        logger.info(f"Starting escalation watcher for {reference_id}")
        poll_interval = float(os.environ.get("ESCALATION_POLL_INTERVAL", "2"))

        try:
            while True:
                await asyncio.sleep(poll_interval)
                status_info = database.get_escalation_status(reference_id)
                if not status_info:
                    continue

                status = status_info.get("status", "open")
                response = status_info.get("human_response")

                if status == "resolved" and response:
                    logger.info(
                        "Escalation %s resolved; interrupting hold music and responding",
                        reference_id,
                    )
                    try:
                        await session.interrupt(force=True)
                    except Exception:
                        logger.exception(
                            "Failed to interrupt current speech for escalation %s",
                            reference_id,
                        )

                    try:
                        handle = session.say(
                            f"A human specialist reviewed your request. {response}",
                            allow_interruptions=False,
                        )
                        await handle.wait_for_playout()
                    except Exception:
                        logger.exception(
                            "Failed to speak human escalation response for %s",
                            reference_id,
                        )
                    return
        except asyncio.CancelledError:
            logger.info("Escalation watcher cancelled for %s", reference_id)
            raise
        except Exception:
            logger.exception("Escalation watcher failed for %s", reference_id)

    @function_tool
    async def save_caller_info(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str = "en",
        facts: str = "{}",
        escalation_reference: str = "",
    ):
        """Save caller information to memory for future interactions.
        Caller should be asked for permission before saving any personal information.

        Args:
            user_id: Unique identifier for the caller
            name: Caller's name
            language_preference: Preferred language code (e.g., 'en', 'hi')
            facts: JSON string containing relevant facts about the caller
            escalation_reference: Optional active escalation reference to save with the caller
        """
        logger.info("=== SAVE_CALLER_INFO CALLED ===")
        logger.info(f"user_id: {user_id}")
        logger.info(f"name: {name}")
        logger.info(f"language_preference: {language_preference}")
        logger.info(f"facts JSON: {facts}")

        normalized_name = name.strip()
        if not normalized_name:
            logger.error("Caller name is required before saving caller info")
            return "I still need the caller's name before I can save this information."

        # Parse facts from JSON string
        try:
            facts_dict = json.loads(facts)
            logger.info(f"Parsed facts dict: {facts_dict}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse facts JSON: {e}")
            facts_dict = {}

        if escalation_reference:
            facts_dict["escalation_ref"] = escalation_reference

        logger.info(f"Facts to save: {facts_dict}")
        success = database.save_caller(
            user_id,
            normalized_name,
            language_preference,
            facts_dict,
            escalation_reference or facts_dict.get("escalation_ref"),
        )

        if success:
            logger.info(
                f"Successfully saved information for {normalized_name} (user_id: {user_id})"
            )
            return f"Successfully saved information for {normalized_name} (user_id: {user_id})"
        else:
            logger.error(f"Failed to save information for user_id: {user_id}")
            return f"Failed to save information for user_id: {user_id}"

    @function_tool
    async def find_clinics(
        self, context: RunContext, location: str, specialty: str = "general practice"
    ):
        """Use this tool to find clinics in a specific area for a given specialty.

        Args:
            location: The area or city to search for clinics (e.g., "Bangalore", "Delhi")
            specialty: The medical specialty (e.g., "cardiology", "pediatrics", "general practice")
        """
        logger.info(f"Finding clinics in {location} for {specialty}")

        # Mock clinic data - in a real implementation, this would call a healthcare API
        mock_clinics = {
            "bangalore": {
                "general practice": [
                    {
                        "name": "Apollo Clinic",
                        "address": "JP Nagar, Bangalore",
                        "rating": 4.5,
                    },
                    {
                        "name": "Manipal Clinic",
                        "address": "Whitefield, Bangalore",
                        "rating": 4.3,
                    },
                    {
                        "name": "Fortis La Femme",
                        "address": "Richmond Town, Bangalore",
                        "rating": 4.4,
                    },
                ],
                "cardiology": [
                    {
                        "name": "Narayana Health",
                        "address": "Bommasandra, Bangalore",
                        "rating": 4.7,
                    },
                    {
                        "name": "Manipal Hospital",
                        "address": "Whitefield, Bangalore",
                        "rating": 4.6,
                    },
                ],
                "pediatrics": [
                    {
                        "name": "Cloudnine Hospital",
                        "address": "Bellandur, Bangalore",
                        "rating": 4.6,
                    },
                    {
                        "name": "Motherhood Hospital",
                        "address": "Sarjapur Road, Bangalore",
                        "rating": 4.4,
                    },
                ],
            },
            "delhi": {
                "general practice": [
                    {"name": "Apollo Hospital", "address": "Delhi", "rating": 4.6},
                    {
                        "name": "Fortis Escorts",
                        "address": "Nehru Place, Delhi",
                        "rating": 4.4,
                    },
                ]
            },
        }

        location_key = location.lower()
        if (
            location_key in mock_clinics
            and specialty.lower() in mock_clinics[location_key]
        ):
            clinics = mock_clinics[location_key][specialty.lower()]
            if clinics:
                response = f"Found {len(clinics)} {specialty} clinics in {location}:\n"
                for clinic in clinics:
                    response += f"• {clinic['name']} - {clinic['address']} (Rating: {clinic['rating']}/5)\n"
                return response

        # Enhanced fallback for demo purposes - provide realistic clinic information for major Indian cities
        major_metros = [
            "mumbai",
            "chennai",
            "kolkata",
            "hyderabad",
            "pune",
            "ahmedabad",
            "jaipur",
            "lucknow",
            "kanpur",
            "nagpur",
            "indore",
            "thane",
            "bhopal",
            "visakhapatnam",
            "pimpri-chinchwad",
            "vadodara",
            "ghaziabad",
            "ludhiana",
            "agra",
            "nashik",
            "faridabad",
            "meerut",
            "rajkot",
            "kalyan-dombivali",
            "vasai-virar",
            "varanasi",
            "srinagar",
            "aurangabad",
            "dhanbad",
            "amritsar",
            "navi mumbai",
            "allahabad",
            "ranchi",
            "howrah",
            "coimbatore",
            "jabalpur",
            "gwalior",
            "vijayawada",
            "jodhpur",
            "madurai",
            "raipur",
            "kota",
            "guwahati",
            "chandigarh",
            "solapur",
            "hubli–dharwad",
            "tiruchirappalli",
            "bareilly",
            "mysore",
            "tiruppur",
            "gurgaon",
            "aligarh",
            "jalandhar",
        ]

        if location_key in major_metros:
            # Generate realistic demo clinic data for major metros
            hospital_chains = [
                {"name": "Apollo Hospital", "rating": "4.5"},
                {"name": "Fortis Hospital", "rating": "4.4"},
                {"name": "Max Super Specialty Hospital", "rating": "4.3"},
                {"name": "Medanta - The Medicity", "rating": "4.6"},
                {"name": "Manipal Hospitals", "rating": "4.2"},
            ]

            # Select 2-3 hospitals randomly for variety
            import random

            selected_hospitals = random.sample(
                hospital_chains, min(3, len(hospital_chains))
            )

            response = f"Found {len(selected_hospitals)} {specialty} clinics in {location.title()} (Demo Information):\n"
            for hospital in selected_hospitals:
                # Generate a plausible address
                areas = [
                    "MG Road",
                    "Park Street",
                    "Connaught Place",
                    "Banerji Road",
                    "Anna Salai",
                    "FC Road",
                    "Diamond Harbour Road",
                ]
                area = random.choice(areas)
                response += f"• {hospital['name']} - {area}, {location.title()} (Rating: {hospital['rating']}/5)\n"

            response += "\nNote: This is demo information. For actual clinic details, please verify with local healthcare directories or hospital websites."
            return response
        else:
            return f"I couldn't find any {specialty} clinics in {location}. Please try a different location or specialty."

    @function_tool
    async def get_appointment_preparation(
        self, context: RunContext, appointment_type: str
    ):
        """Use this tool to get specific preparation guidance for a medical appointment.

        Args:
            appointment_type: The type of medical appointment (e.g., "blood test", "vaccination", "consultation", "x-ray")
        """
        logger.info(f"Getting preparation guidance for {appointment_type}")

        # Mock preparation guidelines
        preparation_guides = {
            "blood test": {
                "fasting": "Usually required for 8-12 hours before the test",
                "what_to_bring": ["Doctor's prescription", "ID card", "Insurance card"],
                "tips": [
                    "Stay hydrated unless otherwise instructed",
                    "Wear a short-sleeved shirt for easy access",
                ],
                "avoid": [
                    "Alcohol for 24 hours before",
                    "Heavy exercise immediately before",
                ],
            },
            "vaccination": {
                "fasting": "Not typically required",
                "what_to_bring": [
                    "Vaccination record/card",
                    "ID card",
                    "Insurance information",
                ],
                "tips": [
                    "Wear clothing that allows easy access to upper arm",
                    "Stay hydrated",
                    "Plan to rest for 15-30 minutes after",
                ],
                "avoid": ["Strenuous activity immediately after vaccination"],
            },
            "consultation": {
                "fasting": "Not required unless specifically advised by doctor",
                "what_to_bring": [
                    "List of current medications",
                    "Medical history notes",
                    "Insurance card",
                    "ID",
                ],
                "tips": [
                    "Write down your symptoms and questions beforehand",
                    "Note when symptoms started and what makes them better/worse",
                ],
                "avoid": ["Going without noting important health changes"],
            },
            "x-ray": {
                "fasting": "Not usually required",
                "what_to_bring": [
                    "Doctor's referral",
                    "ID card",
                    "Previous imaging reports if available",
                ],
                "tips": [
                    "Wear loose, comfortable clothing without metal accessories",
                    "You may need to change into a hospital gown",
                ],
                "avoid": [
                    "Wearing jewelry or clothing with metal zippers/buttons in the imaging area"
                ],
            },
        }

        appointment_key = appointment_type.lower().strip()
        if appointment_key in preparation_guides:
            guide = preparation_guides[appointment_key]
            response = f"Preparation guide for {appointment_type} appointment:\n\n"
            response += f"���🍽��️ Fasting: {guide['fasting']}\n\n"
            response += f"���📋 What to bring: {', '.join(guide['what_to_bring'])}\n\n"
            response += f"���💡 Tips: {', '.join(guide['tips'])}\n\n"
            response += f"��⚠��️ Avoid: {', '.join(guide['avoid'])}"
            return response

        return f"I don't have specific preparation guidelines for {appointment_type} appointments. For general guidance, please bring your ID, insurance information, and any doctor's notes or prescriptions."

    @function_tool
    async def book_appointment(
        self,
        context: RunContext,
        location: str,
        specialty: str,
        preferred_date: str,
        preferred_time: str,
        patient_name: str,
        symptoms: str = "",
    ):
        """Book a medical appointment at a clinic (demo version).

        Args:
            location: The area or city for the appointment (e.g., "Bangalore", "Delhi")
            specialty: The medical specialty (e.g., "cardiology", "pediatrics", "general practice")
            preferred_date: Preferred date for the appointment (e.g., "2026-08-15")
            preferred_time: Preferred time for the appointment (e.g., "10:30 AM")
            patient_name: Name of the patient
            symptoms: Optional symptoms or reason for the visit
        """
        logger.info("=== BOOK_APPOINTMENT CALLED ===")
        logger.info(f"location: {location}")
        logger.info(f"specialty: {specialty}")
        logger.info(f"preferred_date: {preferred_date}")
        logger.info(f"preferred_time: {preferred_time}")
        logger.info(f"patient_name: {patient_name}")
        logger.info(f"symptoms: {symptoms}")

        # In a real implementation, this would call a healthcare API
        # For demo purposes, we'll simulate booking

        # Validate inputs
        if (
            not location
            or not specialty
            or not preferred_date
            or not preferred_time
            or not patient_name
        ):
            return "Please provide all required information: location, specialty, preferred date, preferred time, and patient name."

        # Find clinics to confirm availability
        clinics_result = await self.find_clinics(context, location, specialty)

        if (
            "couldn't find any" in clinics_result.lower()
            or "could not find any" in clinics_result.lower()
        ):
            return f"I couldn't find any {specialty} clinics in {location} to book an appointment. Please try a different location or specialty."

        # Simulate successful booking
        import random

        confirmation_number = f"APT{random.randint(10000, 99999)}"

        response = "Appointment booked successfully!\n\n"
        response += "���📋 Appointment Details:\n"
        response += f"• Patient: {patient_name}\n"
        response += f"• Specialty: {specialty}\n"
        response += f"• Location: {location}\n"
        response += f"• Date: {preferred_date}\n"
        response += f"• Time: {preferred_time}\n"
        if symptoms:
            response += f"• Symptoms: {symptoms}\n"
        response += f"• Confirmation Number: {confirmation_number}\n\n"
        response += "Note: This is a demo appointment. In a real system, you would receive a confirmation via SMS or email.\n"
        response += "Please arrive 15 minutes before your scheduled time."

        return response

    @function_tool
    async def assess_symptoms_urgency(
        self,
        context: RunContext,
        symptoms: str,
    ):
        """Assess the urgency of symptoms based on standard medical guidelines to determine if emergency, urgent, or routine care is needed.
        Enhanced with free NIH/FDA medication interaction checks.

        Args:
            symptoms: Description of symptoms experienced by the user
        """
        logger.info("=== ASSESS_SYMPTOMS_URGENCY CALLED ===")

        # Handle None symptoms
        if symptoms is None:
            symptoms_str = ""
        else:
            symptoms_str = str(symptoms)

        logger.info(f"symptoms: {symptoms_str}")

        # NEW: First check if symptoms might be medication-related using free government APIs
        med_guidance = self._check_medication_side_effects(symptoms_str)
        if med_guidance:
            return med_guidance

        try:
            # Convert to lowercase for easier matching
            symptoms_lower = symptoms_str.lower().strip()

            # Emergency symptoms requiring immediate attention (call ambulance or go to ER)
            emergency_indicators = [
                "chest pain",
                "heart attack",
                "heart pain",
                "difficulty breathing",
                "shortness of breath",
                "can't breathe",
                "breathlessness",
                "severe bleeding",
                "uncontrolled bleeding",
                "bleeding heavily",
                "sudden weakness",
                "weakness on one side",
                "facial drooping",
                "slurred speech",
                "stroke",
                "severe headache",
                "worst headache of life",
                "worst headache ever",
                "worst headache of my life",
                "loss of consciousness",
                "fainting",
                "unconscious",
                "severe burns",
                "major trauma",
                "broken bone",
                "compound fracture",
                "choking",
                "obstructed airway",
                "severe abdominal pain",
                "rigid abdomen",
                "suicidal",
                "self harm",
                "want to die",
                "suicide",
            ]

            # Urgent symptoms requiring same-day medical attention
            urgent_indicators = [
                "high fever",
                "fever over 102",
                "fever over 39",
                "very high fever",
                "moderate bleeding",
                "persistent bleeding",
                "vomiting blood",
                "blood in vomit",
                "blood in stool",
                "rectal bleeding",
                "blood in my stool",
                "severe vomiting",
                "continuous vomiting",
                "severe diarrhea",
                "watery diarrhea",
                "difficulty swallowing",
                "drooling",
                "severe pain",
                "excruciating pain",
                "unbearable pain",
                "severe abdominal pain",
                "excruciating abdominal pain",
                "swelling face",
                "swollen lips",
                "swollen tongue",
                "allergic reaction",
                "moderate asthma attack",
                "wheezing",
                "urinary blockage",
                "can't urinate",
                "testicular pain",
                "scrotal pain",
                "pregnant with bleeding",
                "pregnant with pain",
                "high fever with rash",
                "fever with stiff neck",
                "stiff neck with fever",
            ]

            # Check for emergency symptoms
            for indicator in emergency_indicators:
                if indicator in symptoms_lower:
                    return f"""Based on the symptoms you've described ({symptoms}), this appears to be a MEDICAL EMERGENCY.

Immediate actions required:
• Call emergency services immediately (dial 108 in India for ambulance)
• Or go to the nearest hospital emergency room right away
• Do not delay seeking emergency care

This assessment is based on standard medical emergency guidelines. When in doubt, always err on the side of caution and seek immediate medical attention."""

            # Check for urgent symptoms
            for indicator in urgent_indicators:
                if indicator in symptoms_lower:
                    return f"""Based on the symptoms you've described ({symptoms}), this requires URGENT medical attention within 24 hours.

Recommended actions:
• Contact your doctor today or visit an urgent care clinic
• If symptoms worsen before seeing a doctor, seek emergency care
• Monitor symptoms closely and seek immediate help if you develop emergency symptoms like chest pain, difficulty breathing, or severe bleeding

This assessment is based on standard medical guidelines. This is not a diagnosis but a determination of how quickly you should seek medical evaluation."""

            # Default to routine care for mild or unspecified symptoms
            return f"""Based on the symptoms you've described ({symptoms}), this appears suitable for ROUTINE medical evaluation.

Recommended actions:
• Schedule an appointment with your primary care physician
• Monitor symptoms and seek care if they worsen or persist beyond a few days
• Practice self-care: rest, hydration, and over-the-counter remedies as appropriate for your symptoms
• Seek urgent care if symptoms worsen or you develop concerning signs like fever, increasing pain, or changes in mental status

This assessment is based on standard medical guidelines for symptom triage. This is not medical advice but guidance on when to seek evaluation."""

        except Exception as e:
            logger.error(f"Error in assess_symptoms_urgency: {e}")
            return "I'm unable to assess the severity of your symptoms at the moment due to a technical issue. For any concerning symptoms, please err on the side of caution and consult with a healthcare provider. If you're experiencing severe symptoms like chest pain, difficulty breathing, or severe bleeding, seek emergency medical care immediately."

    def _check_medication_side_effects(self, symptoms_text):
        """Check if symptoms might be medication-related using free NIH/FDA APIs.
        Returns guidance if medication link found, None otherwise.
        """
        try:
            # Extract potential medication names from the text
            # Look for patterns like: "taking X", "on X", "since starting X", etc.
            med_patterns = [
                r"(?:taking|took|on|using|prescribed|since\s+starting|after\s+taking)\s+([a-zA-Z][a-zA-Z\-]+)",
                r"([a-zA-Z][a-zA-Z\-]+)\s+(?:causing|gave|made\s+me|side\s+effect|adverse\s+reaction)",
                r"(?:medicine|medication|drug|pill)s?\s+([a-zA-Z][a-zA-Z\-]+)",
                r"([a-zA-Z][a-zA-Z\-]+)\s+tablet|capsule|drug",
            ]

            potential_meds = set()  # Use set to avoid duplicates

            for pattern in med_patterns:
                matches = re.findall(pattern, symptoms_text, re.IGNORECASE)
                for match in matches:
                    # Filter out common false positives
                    if match.lower() not in [
                        "the",
                        "and",
                        "for",
                        "with",
                        "have",
                        "been",
                        "this",
                        "that",
                        "feel",
                        "having",
                    ]:
                        potential_meds.add(match.lower())

            # Limit to reasonable number to prevent excessive API calls
            potential_meds = list(potential_meds)[:3]

            if not potential_meds:
                return None

            logger.info(f"Checking potential medications: {potential_meds}")

            # Check each potential medication
            for med_name in potential_meds:
                try:
                    # Step 1: Get RxNorm ID for the medication (free, no auth)
                    rxnorm_url = f"https://rxnav.nlm.nih.gov/REST/approximateTerm.json?term={med_name}&maxEntries=1"
                    rxnorm_resp = requests.get(rxnorm_url, timeout=3)

                    if rxnorm_resp.status_code != 200:
                        logger.debug(
                            f"RxNorm lookup failed for {med_name}: {rxnorm_resp.status_code}"
                        )
                        continue

                    rxnorm_data = rxnorm_resp.json()
                    candidates = rxnorm_data.get("approximateTerm", {}).get(
                        "candidate", []
                    )

                    if not candidates:
                        logger.debug(f"No RxNorm candidates found for {med_name}")
                        continue

                    rxcui = candidates[0]["rxcui"]
                    med_display_name = candidates[0]["name"]
                    logger.info(
                        f"Found RxNorm ID {rxcui} for {med_name} -> {med_display_name}"
                    )

                    # Step 2: Check DailyMed for side effects/adverse reactions (free, no auth)
                    dailymed_url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{rxcui}.json"
                    dailymed_resp = requests.get(dailymed_url, timeout=5)

                    if dailymed_resp.status_code != 200:
                        logger.debug(
                            f"DailyMed lookup failed for {rxcui}: {dailymed_resp.status_code}"
                        )
                        # Try OpenFDA as fallback
                        if self._check_openfda_adae(med_display_name, symptoms_text):
                            return self._generate_medication_guidance(
                                med_display_name, symptoms_text
                            )
                        continue

                    # Parse DailyMed XML/JSON for adverse reactions section
                    try:
                        med_data = dailymed_resp.json()
                        # Look for sections related to adverse reactions/side effects
                        spl_sections = med_data.get("spl", {}).get("section", [])

                        adverse_found = False
                        for section in spl_sections:
                            title = section.get("title", "").lower()
                            if any(
                                keyword in title
                                for keyword in [
                                    "adverse",
                                    "side effect",
                                    "undesirable",
                                    "reaction",
                                ]
                            ):
                                text_content = str(section.get("text", ""))
                                # Simple check: if any symptom keywords appear in the side effects text
                                symptom_words = symptoms_text.lower().split()
                                if any(
                                    word in text_content.lower()
                                    for word in symptom_words
                                    if len(word) > 3
                                ):
                                    adverse_found = True
                                    break

                        if adverse_found:
                            return self._generate_medication_guidance(
                                med_display_name, symptoms_text
                            )

                    except (ValueError, KeyError, TypeError) as parse_error:
                        logger.debug(
                            f"Could not parse DailyMed JSON for {rxcui}: {parse_error}"
                        )
                        # Continue to try OpenFDA

                    # Step 3: Fallback to OpenFDA adverse event database
                    if self._check_openfda_adae(med_display_name, symptoms_text):
                        return self._generate_medication_guidance(
                            med_display_name, symptoms_text
                        )

                except Exception as med_error:
                    logger.debug(f"Medication check failed for {med_name}: {med_error}")
                    continue  # Try next medication

            return None  # No medication link found after checking all candidates

        except Exception as e:
            logger.debug(
                f"Medication side effect check encountered error (non-critical): {e}"
            )
            return None  # Fail gracefully - don't break main symptom assessment

    def _check_openfda_adae(self, medication_name, symptoms_text):
        """Check OpenFDA for adverse event reports linking medication to symptoms."""
        try:
            # Clean medication name for search
            clean_med = medication_name.lower().strip()

            # OpenFDA adverse events endpoint
            # Search for reports where patient took this medication and experienced symptoms similar to user's
            symptoms_for_search = "%20".join(
                symptoms_text.lower().split()[:3]
            )  # First 3 significant words

            openfda_url = f"https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:{clean_med}+AND+patient.reaction.reactionmeddrapt:{symptoms_for_search}&limit=1"

            response = requests.get(openfda_url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                return len(results) > 0  # Found at least one matching report

            return False
        except Exception as e:
            logger.debug(f"OpenFDA check failed: {e}")
            return False

    def _generate_medication_guidance(self, medication_name, symptoms_text):
        """Generate guidance when medication-side effect link is found."""
        return f"""Based on your description, this symptom might be related to medication you're taking.

{medication_name.title()} has been associated with similar symptoms in some patients.

Important: Do not stop any medication without consulting your doctor or pharmacist.
Please speak with your healthcare provider about whether this symptom could be a side effect.

If symptoms are severe or worsening, seek medical attention.
If you suspect this is a side effect, your doctor may be able to adjust your dosage or switch medications."""

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        user_id: str,
        summary: str,
        urgency: str,
        language: str = "en",
        next_step: str = "wait",
        caller_name: str = "",
        caller_facts: str = "{}",
    ):
        """Create a human escalation request when the user has a red flag symptom or needs a diagnosis.
        Call this ONLY if the user gave permission to escalate.

        Args:
            user_id: Unique identifier for the caller
            summary: Short description of the medical issue or question (without PII)
            urgency: 'low', 'medium', 'high', or 'emergency'
            language: The language the user is speaking ('en' or 'hi')
            next_step: What the caller wants to do after escalation creation: 'wait' or 'call_later'
            caller_name: The caller's name when they want to call back later
            caller_facts: JSON string of any facts to store with the callback record
        """
        logger.info(f"=== CREATE_ESCALATION CALLED ===")
        try:
            ref_id = database.create_escalation(user_id, summary, urgency, language)

            normalized_step = (next_step or "wait").strip().lower()
            if normalized_step == "call_later":
                normalized_name = caller_name.strip()
                if not normalized_name:
                    return (
                        "I still need the caller's full name before I can save callback details. "
                        "Please ask for their name first, then create the escalation again."
                    )

                try:
                    facts_dict = json.loads(caller_facts) if caller_facts else {}
                except json.JSONDecodeError:
                    logger.warning("Invalid callback facts JSON; saving escalation ref only")
                    facts_dict = {}

                facts_dict["escalation_ref"] = ref_id
                database.save_caller(
                    user_id,
                    normalized_name,
                    language,
                    facts_dict,
                    escalation_reference=ref_id,
                )
                return (
                    f"Successfully created escalation. The Reference ID is {ref_id}. "
                    f"I saved the callback details for {normalized_name}."
                )

            if ref_id not in self._escalation_watch_tasks or self._escalation_watch_tasks[
                ref_id
            ].done():
                watch_task = asyncio.create_task(
                    self._monitor_escalation_resolution(context.session, ref_id)
                )
                self._escalation_watch_tasks[ref_id] = watch_task

                def _cleanup_watch_task(task: asyncio.Task[None]) -> None:
                    self._escalation_watch_tasks.pop(ref_id, None)

                watch_task.add_done_callback(_cleanup_watch_task)

            return (
                f"Successfully created escalation. The Reference ID is {ref_id}. "
                "Would you like me to play hold music while you wait?"
            )
        except Exception as e:
            logger.error(f"Failed to create escalation: {e}")
            return "Failed to create escalation due to a technical error."

    @function_tool
    async def check_escalation_status(self, context: RunContext, reference_id: str):
        """Check the status of a human escalation request. Use this while the user is waiting on hold, or when they call back.

        Args:
            reference_id: The Reference ID provided when the escalation was created
        """
        logger.info(f"=== CHECK_ESCALATION_STATUS CALLED for {reference_id} ===")
        status_info = database.get_escalation_status(reference_id)

        if not status_info:
            return f"I couldn't find an escalation with Reference ID {reference_id}."

        status = status_info.get("status", "open")
        response = status_info.get("human_response")

        if status == "resolved" and response:
            return f"The request is resolved. The human specialist said: {response}"
        else:
            return "The request is still open and waiting for a human specialist to respond."

    @function_tool
    async def play_hold_music(
        self,
        context: RunContext,
    ):
        """Play relaxing hold music for the caller while they wait for a human response."""
        logger.info("=== PLAY_HOLD_MUSIC CALLED ===")
        try:
            session = context.session
            audio_path = os.path.join(os.path.dirname(__file__), "music.mp3")
            if not os.path.exists(audio_path):
                logger.error(f"Hold music file not found at {audio_path}")
                return "Hold music file not found. Please wait while a specialist reviews your request."
            from livekit.agents.utils.audio import AudioByteStream
            import av

            with av.open(audio_path) as container:
                audio_stream = next(
                    (stream for stream in container.streams if stream.type == "audio"),
                    None,
                )
                if audio_stream is None:
                    logger.error(f"No audio stream found in hold music file {audio_path}")
                    return "Hold music file not found. Please wait while a specialist reviews your request."

                resampler = av.audio.resampler.AudioResampler(
                    format="s16",
                    layout="mono",
                    rate=audio_stream.rate or 48000,
                )

                sample_rate = audio_stream.rate or 48000
                num_channels = 1
                raw_chunks: list[bytes] = []

                for frame in container.decode(audio_stream):
                    resampled = resampler.resample(frame)
                    if resampled is None:
                        continue
                    resampled_frames = resampled if isinstance(resampled, list) else [resampled]
                    for out_frame in resampled_frames:
                        sample_rate = out_frame.sample_rate or sample_rate
                        num_channels = len(out_frame.layout.channels) if out_frame.layout else num_channels
                        raw_chunks.append(out_frame.to_ndarray().tobytes())

            audio_stream = AudioByteStream(
                sample_rate=sample_rate,
                num_channels=num_channels,
            )
            frames = []
            for chunk in raw_chunks:
                frames.extend(audio_stream.push(chunk))
            frames.extend(audio_stream.flush())

            async def _frame_stream():
                for frame in frames:
                    yield frame

            handle = session.say(
                "",
                audio=_frame_stream(),
                allow_interruptions=True,
                add_to_chat_ctx=False,
            )
            await handle.wait_for_playout()
            return "Hold music finished playing."
        except Exception as e:
            logger.error(f"Failed to play hold music: {e}")
            return "Could not play hold music. Please wait while a specialist reviews your request."

    @function_tool
    async def end_call(
        self,
        context: RunContext,
    ):
        """Use this tool to end the current call when the conversation is naturally concluding."""
        logger.info("Ending call as conversation is complete")
        # The actual ending is handled by the session when this tool returns
        # We just need to signal that the conversation is done
        return "Ending the call now. Thank you for using the Health Access Voice Agent."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def _get_job_metadata(ctx: JobContext) -> dict:
    """Extract metadata from job context"""
    try:
        return json.loads(ctx.job.metadata) if ctx.job.metadata else {}
    except:
        return {}


def _get_job_phone(ctx: JobContext) -> str | None:
    """Extract phone number from job metadata for outbound calls"""
    metadata = _get_job_metadata(ctx)
    return metadata.get("phone_number")


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Check if this is an outbound call
    job_metadata = _get_job_metadata(ctx)
    is_outbound = job_metadata.get("phone_number") is not None
    phone_number = job_metadata.get("phone_number") if is_outbound else None

    # Set up a voice AI pipeline using Murf Falcon, Groq/Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=_build_llm(),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
            voice="Anisha",  # Using a known working voice for Murf Falcon
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection="vad",
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Determine call type for the prompt
    call_type = "outbound" if is_outbound else "inbound"

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(call_type=call_type),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    if is_outbound and phone_number:
        # Handle outbound call
        logger.info(f"Starting outbound call to {phone_number}")
        t0 = time.monotonic()
        await _dial_and_greet_outbound(ctx, session, phone_number, t0)
    else:
        # Handle inbound call (normal operation)
        logger.info("Starting inbound call handling")
        await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
