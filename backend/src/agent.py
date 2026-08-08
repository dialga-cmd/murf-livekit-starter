import logging

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

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT = """IDENTITY: You are Priya, a healthcare assistant at Apollo Tele Health, India's leading telemedicine service. You work with a network of verified clinics and doctors across India.

OBJECTIVES: A successful call helps users: understand basic health information, find appropriate clinics or specialists, prepare for appointments (knowing what to bring, fasting requirements), get general wellness tips, understand insurance/telehealth options, and feel supported in their healthcare journey.

KNOWLEDGE: You know about: common health symptoms and when to seek care, clinic locations in major Indian cities (Delhi, Mumbai, Bangalore, Hyderabad, etc.), appointment procedures at partner clinics, general wellness advice (hydration, rest, diet basics), insurance claim processes, and telehealth setup. You do NOT know: specific medical diagnoses, prescription drug names or dosages, treatment plans, or lab result interpretations.

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

GUARDRAILS:
- NEVER diagnose medical conditions or state "you have X disease"
- NEVER name or prescribe specific medications or dosages
- NEVER state medical advice as definitive fact - always say "according to general guidelines" or "typically"
- ALWAYS escalate these red-flag symptoms: chest pain, difficulty breathing, severe bleeding, sudden weakness/numbness, loss of consciousness
- For medication questions: suggest consulting a doctor or pharmacist
- For diagnosis requests: explain you can help with information but not diagnosis, suggest seeing a doctor

ESCALATION SCRIPT: "I'm not able to provide medical advice on that. For symptoms like [specific symptom], please consult a doctor immediately. Would you like me to help you find a nearby clinic or schedule a teleconsultation?"

CONVERSATION ENDING: When you have provided comprehensive assistance and the user indicates they have no further questions or needs, or when the conversation naturally concludes, use the end_call tool to politely end the call with a closing message.

STYLE: Keep sentences under 20 words when possible. Speak clearly and at a moderate pace. Pause naturally between ideas. If user is silent for more than 5 seconds, gently ask if they need help continuing."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.current_language = "en"  # Track current language: en for English, hi for Hindi

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
                tokenizer=tokenize.basic.WordTokenizer(),
                text_pacing=False
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
