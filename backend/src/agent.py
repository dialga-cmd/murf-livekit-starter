import logging
import os
import json
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation

# Import our database module
import database

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT = """IDENTITY: You are Priya, a healthcare assistant at Apollo Tele Health, India's leading telemedicine service. You work with a network of verified clinics and doctors across India.

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
- Always maintain your identity as Priya, a female healthcare assistant. Use feminine terms and respectful tone appropriate for Priya.

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

GUARDRAILS:
- NEVER diagnose medical conditions or state "you have X disease"
- NEVER name or prescribe specific medications or dosages
- NEVER state medical advice as definitive fact - always say "according to general guidelines" or "typically"
- ALWAYS escalate these red-flag symptoms: chest pain, difficulty breathing, severe bleeding, sudden weakness/numbness, loss of consciousness
- For medication questions: suggest consulting a doctor or pharmacist
- For diagnosis requests: explain you can help with information but not diagnosis, suggest seeing a doctor

ESCALATION SCRIPT: "I'm not able to provide medical advice on that. For symptoms like [specific symptom], please consult a doctor immediately. Would you like me to help you find a nearby clinic or schedule a teleconsultation?"

CONVERSATION ENDING:
- After you have provided assistance, pause briefly
- Ask the user: "Do you have any other questions or need help with anything else?"
- Wait for their response
- If they indicate they do not have further questions or needs, ask for permission to end the call: "May I end the call now?"
- Wait for their response
- If they agree (say yes or equivalent), use the end_call tool to end the call with a polite goodbye message
- If they have more questions, continue to assist them

STYLE: Keep sentences under 20 words when possible. Speak clearly and at a moderate pace. Pause naturally between ideas. If user is silent for more than 5 seconds, gently ask if they need help continuing."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.current_language = "en"  # Track current language: en for English, hi for Hindi

    @function_tool
    async def look_up_caller(
        self,
        context: RunContext,
        user_id: str,
    ):
        """Look up a caller's information from memory using their user ID.

        Args:
            user_id: Unique identifier for the caller (e.g., phone number, anonymous ID)
        """
        logger.info(f"=== LOOK_UP_CALLER CALLED ===")
        logger.info(f"user_id: {user_id}")
        caller_info = database.get_caller(user_id)

        if caller_info:
            logger.info(f"Found caller info for {user_id}: {caller_info['name']}")
            logger.info(f"Caller info details: {caller_info}")
            return f"Found caller info: Name: {caller_info['name']}, Language: {caller_info['language_preference']}, Facts: {json.dumps(caller_info['facts'])}"
        else:
            logger.info(f"No prior information found for user_id: {user_id}")
            return f"No prior information found for user_id: {user_id}. This appears to be a new caller."

    @function_tool
    async def save_caller_info(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str = "en",
        facts: str = "{}",
    ):
        """Save caller information to memory for future interactions.
        Caller should be asked for permission before saving any personal information.

        Args:
            user_id: Unique identifier for the caller
            name: Caller's name
            language_preference: Preferred language code (e.g., 'en', 'hi')
            facts: JSON string containing relevant facts about the caller
        """
        logger.info(f"=== SAVE_CALLER_INFO CALLED ===")
        logger.info(f"user_id: {user_id}")
        logger.info(f"name: {name}")
        logger.info(f"language_preference: {language_preference}")
        logger.info(f"facts JSON: {facts}")

        # Parse facts from JSON string
        try:
            facts_dict = json.loads(facts)
            logger.info(f"Parsed facts dict: {facts_dict}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse facts JSON: {e}")
            facts_dict = {}

        logger.info(f"Facts to save: {facts_dict}")
        success = database.save_caller(user_id, name, language_preference, facts_dict)

        if success:
            logger.info(f"Successfully saved information for {name} (user_id: {user_id})")
            return f"Successfully saved information for {name} (user_id: {user_id})"
        else:
            logger.error(f"Failed to save information for user_id: {user_id}")
            return f"Failed to save information for user_id: {user_id}"

    @function_tool
    async def find_clinics(
        self,
        context: RunContext,
        location: str,
        specialty: str = "general practice"
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
                    {"name": "Apollo Clinic", "address": "JP Nagar, Bangalore", "rating": 4.5},
                    {"name": "Manipal Clinic", "address": "Whitefield, Bangalore", "rating": 4.3},
                    {"name": "Fortis La Femme", "address": "Richmond Town, Bangalore", "rating": 4.4}
                ],
                "cardiology": [
                    {"name": "Narayana Health", "address": "Bommasandra, Bangalore", "rating": 4.7},
                    {"name": "Manipal Hospital", "address": "Whitefield, Bangalore", "rating": 4.6}
                ],
                "pediatrics": [
                    {"name": "Cloudnine Hospital", "address": "Bellandur, Bangalore", "rating": 4.6},
                    {"name": "Motherhood Hospital", "address": "Sarjapur Road, Bangalore", "rating": 4.4}
                ]
            },
            "delhi": {
                "general practice": [
                    {"name": "Apollo Hospital", "address": "Delhi", "rating": 4.6},
                    {"name": "Fortis Escorts", "address": "Nehru Place, Delhi", "rating": 4.4}
                ]
            }
        }

        location_key = location.lower()
        if location_key in mock_clinics and specialty.lower() in mock_clinics[location_key]:
            clinics = mock_clinics[location_key][specialty.lower()]
            if clinics:
                response = f"Found {len(clinics)} {specialty} clinics in {location}:\n"
                for clinic in clinics:
                    response += f"• {clinic['name']} - {clinic['address']} (Rating: {clinic['rating']}/5)\n"
                return response

        # Enhanced fallback for demo purposes - provide realistic clinic information for major Indian cities
        major_metros = ["mumbai", "chennai", "kolkata", "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "pimpri-chinchwad", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "faridabad", "meerut", "rajkot", "kalyan-dombivali", "vasai-virar", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar", "navi mumbai", "allahabad", "ranchi", "howrah", "coimbatore", "jabalpur", "gwalior", "vijayawada", "jodhpur", "madurai", "raipur", "kota", "guwahati", "chandigarh", "solapur", "hubli–dharwad", "tiruchirappalli", "bareilly", "mysore", "tiruppur", "gurgaon", "aligarh", "jalandhar"]

        if location_key in major_metros:
            # Generate realistic demo clinic data for major metros
            hospital_chains = [
                {"name": f"Apollo Hospital", "rating": "4.5"},
                {"name": f"Fortis Hospital", "rating": "4.4"},
                {"name": f"Max Super Specialty Hospital", "rating": "4.3"},
                {"name": f"Medanta - The Medicity", "rating": "4.6"},
                {"name": f"Manipal Hospitals", "rating": "4.2"}
            ]

            # Select 2-3 hospitals randomly for variety
            import random
            selected_hospitals = random.sample(hospital_chains, min(3, len(hospital_chains)))

            response = f"Found {len(selected_hospitals)} {specialty} clinics in {location.title()} (Demo Information):\n"
            for hospital in selected_hospitals:
                # Generate a plausible address
                areas = ["MG Road", "Park Street", "Connaught Place", "Banerji Road", "Anna Salai", "FC Road", "Diamond Harbour Road"]
                area = random.choice(areas)
                response += f"• {hospital['name']} - {area}, {location.title()} (Rating: {hospital['rating']}/5)\n"

            response += "\nNote: This is demo information. For actual clinic details, please verify with local healthcare directories or hospital websites."
            return response
        else:
            return f"I couldn't find any {specialty} clinics in {location}. Please try a different location or specialty."

    @function_tool
    async def get_appointment_preparation(
        self,
        context: RunContext,
        appointment_type: str
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
                "tips": ["Stay hydrated unless otherwise instructed", "Wear a short-sleeved shirt for easy access"],
                "avoid": ["Alcohol for 24 hours before", "Heavy exercise immediately before"]
            },
            "vaccination": {
                "fasting": "Not typically required",
                "what_to_bring": ["Vaccination record/card", "ID card", "Insurance information"],
                "tips": ["Wear clothing that allows easy access to upper arm", "Stay hydrated", "Plan to rest for 15-30 minutes after"],
                "avoid": ["Strenuous activity immediately after vaccination"]
            },
            "consultation": {
                "fasting": "Not required unless specifically advised by doctor",
                "what_to_bring": ["List of current medications", "Medical history notes", "Insurance card", "ID"],
                "tips": ["Write down your symptoms and questions beforehand", "Note when symptoms started and what makes them better/worse"],
                "avoid": ["Going without noting important health changes"]
            },
            "x-ray": {
                "fasting": "Not usually required",
                "what_to_bring": ["Doctor's referral", "ID card", "Previous imaging reports if available"],
                "tips": ["Wear loose, comfortable clothing without metal accessories", "You may need to change into a hospital gown"],
                "avoid": ["Wearing jewelry or clothing with metal zippers/buttons in the imaging area"]
            }
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
        logger.info(f"=== BOOK_APPOINTMENT CALLED ===")
        logger.info(f"location: {location}")
        logger.info(f"specialty: {specialty}")
        logger.info(f"preferred_date: {preferred_date}")
        logger.info(f"preferred_time: {preferred_time}")
        logger.info(f"patient_name: {patient_name}")
        logger.info(f"symptoms: {symptoms}")

        # In a real implementation, this would call a healthcare API
        # For demo purposes, we'll simulate booking

        # Validate inputs
        if not location or not specialty or not preferred_date or not preferred_time or not patient_name:
            return "Please provide all required information: location, specialty, preferred date, preferred time, and patient name."

        # Find clinics to confirm availability
        clinics_result = await self.find_clinics(context, location, specialty)

        if "couldn't find any" in clinics_result.lower() or "could not find any" in clinics_result.lower():
            return f"I couldn't find any {specialty} clinics in {location} to book an appointment. Please try a different location or specialty."

        # Simulate successful booking
        import random
        confirmation_number = f"APT{random.randint(10000, 99999)}"

        response = f"Appointment booked successfully!\n\n"
        response += f"���📋 Appointment Details:\n"
        response += f"• Patient: {patient_name}\n"
        response += f"• Specialty: {specialty}\n"
        response += f"• Location: {location}\n"
        response += f"• Date: {preferred_date}\n"
        response += f"• Time: {preferred_time}\n"
        if symptoms:
            response += f"• Symptoms: {symptoms}\n"
        response += f"• Confirmation Number: {confirmation_number}\n\n"
        response += f"Note: This is a demo appointment. In a real system, you would receive a confirmation via SMS or email.\n"
        response += f"Please arrive 15 minutes before your scheduled time."

        return response

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


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-3.5-flash-lite", temperature=0.7, max_output_tokens=150,
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="Anisha",  # Using a known working voice for Murf Falcon
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
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

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
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

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
