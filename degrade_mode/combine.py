#!/usr/bin/env python3
"""
combine.py
Full working script — Bandwidth-aware Agent runner with prompt+token logic.
Replace provider/model configuration where indicated if you want real API calls.
"""

import time
import urllib.request
import os
from dataclasses import dataclass
import math
from dotenv import load_dotenv

# Try to import agent SDK pieces. If absent, we'll still run in simulated mode.
try:
    from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, set_tracing_disabled
    SDK_AVAILABLE = True
except Exception:
    # Provide minimal stubs for local testing if SDK isn't installed.
    SDK_AVAILABLE = False

    class Agent:
        def __init__(self, name=None, instructions=None):
            self.name = name
            self.instructions = instructions
            self.model_settings = None

    class Runner:
        @staticmethod
        def run_sync(starting_agent=None, input=None, model_settings=None):
            # Simulated SDK-like response object
            class Resp:
                def __init__(self, text):
                    self.final_output = text
            # simple echo with a tiny transformation
            out = f"[SIMULATED ANSWER — tokens={getattr(model_settings,'max_tokens', 'N/A')}] " \
                  f"Answer to: {input[:200]}"
            return Resp(out)

    def set_tracing_disabled(flag: bool):
        pass

# ------------------- Bandwidth Check -------------------
def check_bandwidth(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSZtdNNVK-gDIF-vyrnNSy5_SEKN4z0FiwGeQ&s",
                    file_size_bytes=5 * 1024 * 1024,
                    timeout_seconds=10):
    """
    Measures download speed (Mbps) by attempting to read the URL.
    Returns measured Mbps as float; returns 0.0 on error (no connection).
    """
    try:
        start_time = time.time()
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            _ = response.read()  # read entire test resource
        duration = time.time() - start_time
        if duration <= 0:
            return 0.0
        # Convert bytes -> bits and compute megabits per second
        speed_mbps = (file_size_bytes * 8) / (duration * 1_000_000)
        return speed_mbps
    except Exception as e:
        # print debug for developer — in production you might log this
        print(f"Bandwidth check error: {e}")
        return 0.0


# ------------------- ModelSettings (sdk-style fallback) -------------------
try:
    from agents import ModelSettings  # if available in SDK
except Exception:
    @dataclass
    class ModelSettings:
        max_tokens: int = 256
        temperature: float = 0.7
        top_p: float = 1.0


# ------------------- Prompts -------------------
DETAILED_PROMPT = """
You are an experienced computer science and mathematics teacher with 10 years of experience.
Explain how to analyze internet speed to a 12-year-old beginner English learner.
- Use step-by-step explanations, simple language, and everyday examples.
- Explain what internet speed means, how to test it, what is good vs poor speed, and why it matters.
- Dive deeper: explain units (Mbps), what affects speed (Wi-Fi, ISP, congestion), and how to interpret results for streaming/gaming/homework.
- Give a short checklist students can follow and one simple experiment they can run.
Make the answer thorough and educational.
"""

CONCISE_PROMPT = """
You are an experienced teacher. Give a short, essential explanation (strictly <=100 tokens) on how to analyze internet speed for a 12-year-old.
Include 3 quick steps and one very short example. Avoid extra detail.
"""


# ------------------- Token estimation and budgeting -------------------
def estimate_prompt_tokens(prompt_text: str) -> int:
    """
    Rough token estimate: ~0.75 tokens per word for prompts.
    This is a heuristic; for exact counting, integrate tokenizer from your SDK.
    """
    words = len(prompt_text.split())
    return max(10, int(words * 0.75))


def compute_max_tokens(user_input: str, prompt_text: str, stable: bool,
                       min_when_stable: int = 400, max_cap: int = 4096) -> int:
    """
    Compute the available response token budget:
    - If unstable: strict 100 tokens.
    - If stable: compute a generous budget based on input size and prompt size.
      Heuristic: estimated_total = clamp(words * 50, min_when_stable, max_cap)
      available = estimated_total - prompt_tokens (clamped to reasonable range)
    """
    if not stable:
        return 100

    words = len(user_input.split()) if user_input else 10
    estimated_total_tokens = max(min_when_stable, min(max_cap, words * 50))
    prompt_tokens = estimate_prompt_tokens(prompt_text)
    available = estimated_total_tokens - prompt_tokens

    # For stable mode we want a detailed reply: ensure at least 300 tokens
    available = max(300, min(max_cap, available))
    return int(available)


# ------------------- Agent Setup -------------------
load_dotenv()
set_tracing_disabled(True)

Agent1 = Agent(
    name="Assistant",
    instructions=DETAILED_PROMPT,  # default; we'll set per-turn
)

# Uncomment and configure your provider/model if you want real API usage:
# provider = AsyncOpenAI(
#     api_key=os.getenv("GEMINI_API_KEY"),
#     base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
# )
#
# model = OpenAIChatCompletionsModel(
#     model="gemini-2.0-flash-exp",
#     openai_client=provider
# )
#
# Optionally attach model to Agent1 depending on your SDK:
# Agent1.model = model


# ------------------- Main routine -------------------
def routine(threshold_mbps: float = 90.0):
    """
    Main interactive loop:
    - Check bandwidth each turn
    - Choose detailed or concise prompt
    - Compute token limits and attach model settings
    - Run the agent (or simulated runner) and print output
    """
    print("Starting interactive loop. Type 'exit', 'quit', or 'bye' to leave.")
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAssistant: Goodbye! 👋")
            break

        if user_input.lower() in ("exit", "quit", "bye"):
            print("Assistant: Goodbye! 👋")
            break

        # 1) Check bandwidth
        speed = check_bandwidth()
        print(f"Current bandwidth: {speed:.2f} Mbps")

        if speed == 0.0:
            print("❌ No internet connection detected. Please check your network.")
            # Optionally we could still answer in local/offline mode, but user wanted network-aware logic
            continue

        stable = speed >= threshold_mbps

        # 2) Choose prompt
        if stable:
            print("✅ Internet stable — using detailed prompt and generous token budget.")
            chosen_prompt = DETAILED_PROMPT
        else:
            print("⚠️ Internet unstable — using concise prompt and strict 100 tokens.")
            chosen_prompt = CONCISE_PROMPT

        # 3) Compute token budget (strict 100 if unstable)
        max_tokens = compute_max_tokens(user_input, chosen_prompt, stable)

        # 4) Create model settings
        model_settings = ModelSettings(max_tokens=max_tokens, temperature=0.35, top_p=1.0)

        # 5) Attach chosen prompt and model settings to the agent and run
        Agent1.instructions = chosen_prompt
        Agent1.model_settings = model_settings  # many SDKs accept this pattern

        # Robust run with try/except to avoid syntax/runtime problems
        try:
            # Preferred call
            response = Runner.run_sync(starting_agent=Agent1, input=user_input)
        except TypeError:
            # Fallback signature with model_settings provided explicitly
            try:
                response = Runner.run_sync(starting_agent=Agent1, input=user_input, model_settings=model_settings)
            except Exception as e:
                print("Error running agent in fallback TypeError:", e)
                response = None
        except Exception as e:
            print("Unexpected error when calling Runner.run_sync:", e)
            response = None

        # 6) Output handling
        if response is None:
            # Simulated reply if SDK call failed
            note = f"(simulated reply — limited to {max_tokens} tokens)"
            simulated = f"[SIMULATED ANSWER] {note}\nShort guide: Measure speed, compare to thresholds, pick test times."
            print("Assistant:", simulated)
        else:
            # Try common SDK shapes to extract text
            out_text = None
            try:
                if hasattr(response, "final_output"):
                    out_text = getattr(response, "final_output")
                elif isinstance(response, dict) and "output" in response:
                    out_text = response["output"]
                elif hasattr(response, "text"):
                    out_text = getattr(response, "text")
                else:
                    out_text = str(response)
            except Exception as e:
                out_text = f"[ERROR extracting response text: {e}]"

            print("Assistant:", out_text)


if __name__ == "__main__":
    # You can change threshold_mbps to whatever you consider "stable"
    routine(threshold_mbps=90.0)




