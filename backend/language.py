import re


HINGLISH_KEYWORDS = {
    "kya",
    "hai",
    "meri",
    "mera",
    "kaise",
    "kab",
    "kahan",
    "kitna",
    "chahiye",
    "batao",
    "nahi",
    "hoga",
    "kaun",
    "kyun",
    "fees",
    "attendance",
    "exam",
    "hostel",
    "scholarship",
    "admission",
    "result",
    "timetable",
    "library",
    "canteen",
}

STRONG_HINGLISH_MARKERS = {
    "kya",
    "hai",
    "meri",
    "mera",
    "kaise",
    "kab",
    "kahan",
    "kitna",
    "chahiye",
    "batao",
    "nahi",
    "hoga",
    "kaun",
    "kyun",
}


def detect_language(text: str) -> str:
    if not text:
        return "english"

    if any("\u0900" <= char <= "\u097f" for char in text):
        return "hindi"

    normalized = text.lower()
    words = set(re.findall(r"[a-zA-Z]+", normalized))
    if words.intersection(STRONG_HINGLISH_MARKERS):
        return "hindi"
    return "english"


def build_system_prompt(language: str, college_name: str) -> str:
    if language == "hindi":
        return f"""
Tum CampusAI ho, jo {college_name} ke students ki madad karta hai.

Strict Rules:
1) Sirf diye gaye context se answer do.
2) Agar context me answer na mile, exactly bolo: "Mujhe pakki jaankari nahi — Admin Office se confirm karein".
3) Kabhi guess mat karo, kabhi information invent mat karo.
4) Har answer ke end me "Source:" likhkar document naam aur page mention karo.
5) Simple Hinglish me jawab do.
6) Har jawab me practical next step do.
7) Fees/date/amount aaye to exact number hi do.
8) Agar uncertainty ho to clearly bolo aur admin se confirm karne ko kaho.
""".strip()

    return f"""
You are CampusAI for {college_name}.

Strict Rules:
1) Answer only from the provided context.
2) If answer is not in context, say exactly: "I don't have reliable info on this. Please contact Admin Office".
3) Never guess. Never invent data.
4) Always cite source document and page at the end as "Source:".
5) Keep responses clear, concise, and helpful.
6) Always provide actionable next steps.
7) For fees/dates/amounts use exact values from context only.
8) If uncertain, explicitly ask student to confirm with Admin Office.
""".strip()


def no_result_message(language: str) -> str:
    if language == "hindi":
        return (
            "Mujhe is sawal ka data college documents me nahi mila. "
            "Mujhe pakki jaankari nahi — Admin Office se confirm karein."
        )
    return (
        "I could not find this information in the college documents. "
        "I don't have reliable info on this. Please contact Admin Office."
    )


def low_confidence_message(language: str) -> str:
    if language == "hindi":
        return (
            "Mujhe milti-julti jaankari mili hai, lekin main isko 100% confirm nahi kar sakta. "
            "Mujhe pakki jaankari nahi — Admin Office se confirm karein."
        )
    return (
        "I found related information, but confidence is low. "
        "I don't have reliable info on this. Please contact Admin Office."
    )
