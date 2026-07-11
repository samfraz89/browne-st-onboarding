# -*- coding: utf-8 -*-
"""Browne St. job descriptions — normalised into the house style.

Each role renders with the same sections as the original Front of House JD:
    Job title · Purpose · Specific duties & responsibilities ·
    General duties & responsibilities · Skills, experience & education

`GENERAL_DUTIES` is shared by every role. To add a new role, append an entry
to JOB_DESCRIPTIONS — no changes to app.py required.

Source: the six .docx files supplied by Browne St. (Jun 2026), cleaned for
typos/consistency and mapped into the existing FOH layout.
"""

# Shared across all roles — the standard Browne St. general obligations.
GENERAL_DUTIES = [
    "Be punctual and work the hours and times specified.",
    "Prioritise workload to ensure work of the greatest importance to the business is undertaken with urgency and to a high standard.",
    "Support and help develop a positive workplace culture.",
    "Demonstrate excellent interpersonal communication skills.",
    "Responsibly manage all business resources within accountability levels.",
    "Undertake all duties and responsibilities outlined in this Position Description and all other duties as required by the business.",
    "Comply with all employment obligations.",
    "Promptly undertake to complete all reasonable and lawful instructions and directions given.",
    "Serve the business in good faith, promoting and protecting the business' best interests.",
    "During work time, and such other times as may be reasonably required, dedicate all effort to the execution and fulfilment of the duties, responsibilities, obligations and instructions related to employment.",
    "Demonstrate through your own actions a commitment to Health and Safety at work when undertaking work or observing others in the workplace.",
]

# Ordered registry. key = stable id used by the form/select; title = display name.
JOB_DESCRIPTIONS = [
    {
        "key": "front-of-house",
        "title": "Front of House",
        "purpose": "To deliver a fantastic customer experience in the restaurant, ensuring adherence to company processes whilst contributing to a fun working environment.",
        "duties": [
            "Complete opening and closing duties as per schedule.",
            "Greet all customers in a friendly and appropriate manner.",
            "See customers to their table and inform them of daily specials.",
            "Use till and EFTPOS correctly. Give correct change.",
            "Take orders from customers, waiting on tables and cleaning tables as required.",
            "Take table bookings over the phone.",
            "Prepare and present cabinet food, ensuring cabinets are kept well stocked and tidy.",
            "Make coffee in accordance with training provided, as and when required.",
            "Go out of your way to help customers in order to create a regular and loyal customer base.",
            "Willingly assist other staff members with customer problems or requests.",
            "Ensure the restaurant is kept clean and tidy in keeping with food safety standards at all times.",
            "Assist in the kitchen when required (e.g. dishes, food prep).",
            "Ensure the coffee station, service areas and bar are well stocked and tidy.",
            "Check customer's identification to ensure minimum age requirements for alcohol consumption are met.",
        ],
        "skills": [
            "Customer facing experience required, and experience in hospitality preferred.",
            "Excellent communication and interpersonal skills.",
            "Team player with a positive attitude.",
            "Experience serving alcohol desirable.",
            "Genuine passion for delivering great service.",
        ],
    },
    {
        "key": "barista",
        "title": "Barista",
        "purpose": "To prepare and serve hot and cold beverages — including various types of coffee and tea — educating customers on our drinks menu, making recommendations based on their preferences, up-selling special items and taking orders, ensuring an excellent drinking experience for every guest.",
        "duties": [
            "Greet customers as they enter.",
            "Give customers drink menus and answer their questions regarding ingredients.",
            "Take orders while paying attention to details (e.g. preferences of coffee blend, dairy and sugar ratios).",
            "Prepare beverages following recipes.",
            "Serve beverages and prepared food.",
            "Receive and process payments (cash and credit cards).",
            "Keep the coffee/bar area clean.",
            "Maintain stock of clean cups and plates.",
            "Check that brewing equipment operates properly and report any maintenance needs to the coffee supplier / owners.",
            "Comply with health and safety regulations.",
            "Communicate customer feedback to managers and recommend new menu items.",
        ],
        "skills": [
            "Previous work experience as a Barista or Front of House.",
            "Hands-on experience with brewing equipment.",
            "Knowledge of sanitation regulations.",
            "Flexibility to work various shifts.",
            "Basic maths skills.",
            "Ability to gauge customers' preferences.",
            "Excellent communication skills.",
        ],
    },
    {
        "key": "bar-manager",
        "title": "Bar Manager",
        "purpose": "To take drink orders, mix and serve beverages to customers at the bar or through wait staff — providing an unforgettable experience through great customer service and drinks prepared to a high standard — while managing the bar's operations, stock and team.",
        "duties": [
            "Assess customers' needs and preferences and make recommendations.",
            "Interact with customers, take orders and serve food and drinks.",
            "Mix ingredients to prepare cocktails and help implement seasonal cocktail menus.",
            "Prepare and serve alcoholic and/or non-alcoholic beverages.",
            "Clean glasses, utensils and bar equipment.",
            "Plan and present the food menu.",
            "Restock the bar with beer, wine, liquor, non-alcoholic drinks and related supplies including ice, glassware, napkins and straws.",
            "Take regular inventory of supplies for restocking the bar.",
            "Stay guest-focused and nurture an excellent guest experience.",
            "Collect money for drinks served.",
            "Balance cash receipts.",
            "Make suggestions to management for new drinks recipes.",
            "Check customers' identification and confirm it meets the legal drinking age.",
            "Host Responsibility — limit problems and liability related to customers' excessive drinking by taking steps such as persuading customers to stop drinking, or arranging taxis or other transport for intoxicated patrons.",
            "Comply with all food and beverage regulations and Health & Safety requirements.",
            "Encourage a positive attitude amongst staff and be aware of wage costs and business expenses.",
            "Drive new business and entice regulars.",
        ],
        "skills": [
            "Proven experience as a Bar Manager or in a senior bar / hospitality role.",
            "Manager's Certificate (LCQ) under the Sale and Supply of Alcohol Act 2012, or willingness to obtain one.",
            "Sound knowledge of Host Responsibility and licensing requirements.",
            "Excellent cocktail, wine and beverage knowledge.",
            "Strong leadership, communication and customer service skills.",
            "Ability to manage stock, ordering and cash handling accurately.",
            "Availability to work evenings, weekends and public holidays.",
        ],
    },
    {
        "key": "cafe-manager",
        "title": "Cafe Manager",
        "purpose": "To organise the daily operations of the cafe and motivate the team to provide excellent customer service — scheduling shifts, monitoring expenses and revenue, and ordering supplies — helping to increase profitability, boost customer engagement and make our cafe a favourite local spot.",
        "duties": [
            "Manage the day-to-day operations of the cafe.",
            "Hire and on-board new wait staff and baristas.",
            "Train employees on drinks preparation, proper use of coffee equipment and sequence of service.",
            "Coordinate with vendors and order supplies as needed.",
            "Maintain updated records of daily, weekly and monthly revenues and expenses (including wages).",
            "Add new menu items based on seasonality and customers' preferences (for example, seasonal wine / drinks lists).",
            "Advise staff on the best ways to resolve issues with customers and deliver excellent customer service.",
            "Ensure all cafe areas are clean and tidy.",
            "Nurture friendly relationships with customers to increase loyalty and boost our reputation.",
        ],
        "skills": [
            "Work experience as a Cafe Manager.",
            "Hands-on experience with professional coffee machines.",
            "Good maths skills.",
            "Availability to work within opening hours (including weekends and holidays).",
            "Excellent communication skills with the ability to manage and motivate a team.",
            "Customer service attitude.",
        ],
    },
    {
        "key": "kitchen-hand",
        "title": "Kitchen Hand",
        "purpose": "To maintain cleanliness around the restaurant and kitchen — collecting used dishes, operating dishwashing machines and keeping workstations stocked — helping to provide an unforgettable dining experience for our customers. This role works in shifts, including evenings and weekends.",
        "duties": [
            "Collect used kitchenware from dining and kitchen areas.",
            "Load and unload dishwashing machines.",
            "Wash specific items by hand (e.g. wooden cutting boards, large pots and delicate china).",
            "Store clean dishes, glasses and equipment appropriately.",
            "Set up workstations before meal prep begins.",
            "Ensure there are always enough clean dishes, glasses and utensils, especially during peak hours.",
            "Maintain cleaning supplies stock (e.g. detergents) and place orders when necessary.",
            "Check dishwashing machines' operation and promptly report any technical/performance issues.",
            "Remove garbage regularly.",
            "Sanitise the kitchen area, including the floor.",
        ],
        "skills": [
            "Work experience as a Kitchen Hand or other hospitality job.",
            "Hands-on experience with industrial washing machines.",
            "Ability to follow instructions and help with various tasks as needed.",
            "Time management skills.",
            "Attention to detail and knowledge of sanitation rules.",
            "Availability to work in shifts, during weekends and evenings.",
            "Good communication, both written and verbal.",
        ],
    },
    {
        "key": "chef-de-partie",
        "title": "Chef de Partie",
        "purpose": "To amaze the patrons of our establishment with excellent cooking according to the chef's recipes and specifications. Your work will be an important factor in our customers' satisfaction, helping to expand our clientele and reputation for long-term success.",
        "duties": [
            "Prepare menus in collaboration with colleagues.",
            "Ensure adequacy of supplies at the cooking stations.",
            "Prepare ingredients that should be frequently available (vegetables, spices etc.).",
            "Follow the guidance of the Head or Sous Chef and contribute new ideas for presentation or dishes.",
            "Put effort into optimising the cooking process with attention to speed and quality.",
            "Enforce strict health and hygiene standards.",
            "Help maintain a climate of smooth and friendly cooperation.",
        ],
        "skills": [
            "Proven experience in a Chef de Partie role.",
            "Excellent use of various cooking methods, ingredients, equipment and processes.",
            "Ability to multitask and work efficiently under pressure.",
            "Knowledge of best cooking practices.",
            "Relevant cookery qualifications.",
        ],
    },
    {
        "key": "head-chef",
        "title": "Head Chef",
        "purpose": "To organise and lead the kitchen's activities as first in command — creating and inspecting dishes before they reach the customer to ensure high quality and customer satisfaction.",
        "duties": [
            "Control and direct the food preparation process and any other related activities.",
            "Construct menus with new or existing culinary creations, ensuring the variety and quality of the servings.",
            "Approve and “polish” dishes before they reach the customer.",
            "Plan orders of equipment or ingredients according to identified shortages, and monitor costings of menu items and ingredients.",
            "Arrange for repairs when necessary.",
            "Remedy any problems or defects.",
            "Be fully in charge of hiring, managing and training kitchen staff.",
            "Oversee the work of subordinates.",
            "Estimate staff workload and compensation.",
            "Maintain records of payroll and attendance.",
            "Comply with nutrition and sanitation regulations and safety standards.",
            "Foster a climate of cooperation and respect between co-workers.",
        ],
        "skills": [
            "Proven experience as a Head Chef.",
            "Exceptional proven ability in kitchen management.",
            "Ability to divide responsibilities and monitor progress.",
            "Outstanding communication and leadership skills.",
            "Up-to-date with culinary trends and optimised kitchen processes.",
            "Good understanding of useful computer programs (MS Office, Kounta, Deputy).",
            "Credentials in health and safety training including FCP.",
            "Cookery qualifications Level 4 or similar.",
        ],
    },
]

# Lookups -------------------------------------------------------------------
JD_BY_KEY = {jd["key"]: jd for jd in JOB_DESCRIPTIONS}
JD_BY_TITLE = {jd["title"].lower(): jd for jd in JOB_DESCRIPTIONS}


def get_jd(role):
    """Resolve a role to a JD entry by key or title (case-insensitive).
    Returns None if there's no matching template."""
    if not role:
        return None
    r = role.strip().lower()
    return JD_BY_KEY.get(r) or JD_BY_TITLE.get(r)
