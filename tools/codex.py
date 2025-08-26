import argparse
import os
import ssl

import google.generativeai as palm

# 🚨 Force unverified SSL context only when explicitly enabled
if os.environ.get("CODEX_INSECURE_SSL"):
    ssl._create_default_https_context = ssl._create_unverified_context


def main():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY is not set in environment variables or .env")

    palm.configure(api_key=api_key)
    model = palm.GenerativeModel("models/gemini-1.5-flash")

    parser = argparse.ArgumentParser(description="Codex CLI using Google Generative AI")
    parser.add_argument(
        "prompt",
        type=str,
        help="Prompt to generate code from",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Optional output file to save the result",
    )
    args = parser.parse_args()

    response = model.generate_content(args.prompt)

    if response and response.text:
        print("\n=== GENERATED CODE ===\n")
        print(response.text)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"\n✅ Saved to {args.output}")
    else:

        print("No response from Generative AI.")


if __name__ == "__main__":
    main()
