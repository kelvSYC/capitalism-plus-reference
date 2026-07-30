import json

# SUPERSEDED (see site_template.html's SCENARIOS const for the current, correct
# data). Earlier iterations of this note argued scenarios impose no real sale
# restriction at all -- that was wrong. The restriction is real, and it's now
# fully decoded and verified, not inferred from prose:
#
# Every scenario's .SCN save file embeds a 1-byte-per-ITEMCLAS flag array at a
# fixed offset (315), one byte per row of that gameset's own ITEMCLAS table (in
# table order), 1 = sellable, 0 = excluded. Decoded for all 20 scenarios and
# cross-checked against every scenario's own .SCT text with zero mismatches --
# e.g. Rule Britannia's array has APPAREL/FOOD/LPRODUCT at 0, matching "you
# cannot produce apparel, food, or livestock products" exactly. Confirmed live
# in-game: a Cattle farm built inside Rule Britannia produced Frozen Beef
# (raw_class LPRODUCT -- directly excluded, Sales unit never connects) and Milk
# (raw_class LSEMI -- NOT excluded itself, but its only buyers, Cheese/Yogurt,
# are category Food, which IS excluded, so it has no legal market anywhere),
# while Tallow (also LSEMI) sold fine because its buyer, Soap, is category
# Chemical Products -- not excluded. So restriction is two-layered: direct
# (own raw_class excluded) and indirect (every possible buyer, transitively,
# is excluded or itself stranded). The site computes both live in JS
# (scenarioExcluded / scenarioHasMarket in site_template.html) against the
# verified `excludedClasses` list per scenario -- nothing is guessed anymore.
#
# The `goal_focus_type` / `goal_focus_categories` fields still defined below
# are kept only as a historical record of an earlier, discredited inference
# approach (elimination-by-omission from prose). They are NOT used by the site.

# Category lists per gameset, taken from our own extracted product data (ground truth)
GAMESET_CATEGORIES = {
    "Standard": {"Apparel, Footwear & Bags", "Automobile", "Beverage", "Chemical Products", "Cigarettes",
                 "Computers", "Cosmetics", "Electronic Products", "Food", "Furniture", "Jewelry", "Toys", "Watches"},
    "Alternative": {"Apparel", "Beverage", "Chemical Products", "Cosmetics", "Food", "Home Products",
                    "Household Products", "Jewelry", "Media Products", "Office Equipment", "Optical Products",
                    "Pharmaceuticals", "Sports Equipment", "Toys"},
    "Food & Beverage": {"Beverage", "Canned Food", "Consumer Semi-Products", "Dessert", "Food", "Pasta",
                        "Snacks", "Spice"},
}

# Manually transcribed from each scenario's .SCT text (extracted directly from CapPlus.gog,
# the original install CD image bundled in the game folder -- independent of any prior reference art)
SCENARIOS = [
    {
        "key": "DRAGON", "name": "The Emerging Dragon",
        "goal": "Dominate the chemical and electronic products market; $300M annual profit; 10,000 jobs; within 30 years.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Cigarettes", "Food", "Furniture", "Livestock", "Plant Products"],
        "stock_market_enabled": False,
    },
    {
        "key": "ASIAN", "name": "The Asian Gold Rush",
        "goal": "Dominate manufacturing and retail sectors while producing 20+ product types within 30 years.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Food", "Livestock", "Plant Products"],
        "stock_market_enabled": False,
    },
    {
        "key": "BERLIN", "name": "Fall of the Berlin Wall",
        "goal": "Dominate manufacturing; 15,000 jobs; $400M annual profit; within 20 years.",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": False,
    },
    {
        "key": "BRINK", "name": "Back from the Brink",
        "goal": "40% return-on-equity, $500M annual profit within 25 years.",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": True,
    },
    {
        "key": "DILEMMA", "name": "Diversification Dilemma",
        "goal": "Diversify into 50+ product types, $2B annual revenue, 30% operating margin within 30 years.",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": False,
    },
    {
        "key": "ENTREPRE", "name": "Entrepreneurial Spirit",
        "goal": "$100M annual revenue within 10 years (weak competitors).",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": True,
    },
    {
        "key": "FORTIFY", "name": "Market Fortification",
        "goal": "Control 3+ other companies within 30 years while leading the beverage market, $500M combined profit.",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": True,
    },
    {
        "key": "GLOBAL", "name": "Global Domination",
        "goal": "Achieve market dominance in every market and 100% ownership within 40 years.",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": True,
    },
    {
        "key": "ITALY", "name": "Italy - Looking South",
        "goal": "Dominate manufacturing and retail; $500M annual profit within 25 years.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Automobile", "Cigarettes", "Jewelry"],
        "stock_market_enabled": False,
    },
    {
        "key": "JAPAN", "name": "Japan - Rising from the Ashes",
        "goal": "$500M annual profit, 40% operating margin within 30 years.",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": False,
    },
    {
        "key": "LATECOME", "name": "Latecomer's Ambition",
        "goal": "$10B annual revenue, control 4+ other companies within 40 years.",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": True,
    },
    {
        "key": "RACETIME", "name": "Race Against Time",
        "goal": "$500M annual revenue, $100M annual profit within 6 years.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Jewelry", "Toys", "Household Products", "Home Products"],
        "stock_market_enabled": False,
    },
    {
        "key": "ROUGH", "name": "The Rough Road Ahead",
        "goal": "$50M annual profit, 25+ different products within 15 years (only two cities, far apart).",
        "goal_focus_type": "none",
        "goal_focus_categories": [],
        "stock_market_enabled": False,
    },
    {
        "key": "SILICON", "name": "Silicon Dream",
        "goal": "Major computer-industry player, $5B market value within 35 years, retain 50%+ ownership.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Beverage", "Cigarettes", "Food", "Livestock", "Plant Products",
                                   "Apparel, Footwear & Bags"],
        "stock_market_enabled": True,
    },
    {
        "key": "SPAIN", "name": "The Reign in Spain",
        "goal": "$400M annual profit; dominate manufacturing while retaining farming leadership; within 30 years.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Pharmaceuticals", "Office Equipment", "Household Products", "Home Products"],
        "stock_market_enabled": False,
    },
    {
        "key": "TECHNO", "name": "Techno-Sweep",
        "goal": "Dominate listed markets with $500M annual profit within 35 years (no pre-existing high-tech products; R&D required).",
        "goal_focus_type": "include_only",
        "goal_focus_categories": ["Automobile", "Computers", "Chemical Products", "Electronic Products", "Toys", "Watches"],
        "stock_market_enabled": False,
    },
    {
        "key": "UK", "name": "Rule Britannia",
        "goal": "Dominate mining and manufacturing sectors, $500M annual operating profit within 30 years.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Apparel", "Food", "Livestock"],
        "stock_market_enabled": False,
    },
    {
        "key": "UNDER", "name": "Domination Down Under",
        "goal": "Dominate food, canned food, and snack markets; $400M annual profit; $200M personal wealth within 20 years.",
        "goal_focus_type": "include_only",
        "goal_focus_categories": ["Food", "Canned Food", "Snacks"],
        "stock_market_enabled": True,
    },
    {
        "key": "VERTICAL", "name": "Vertical Integration",
        "goal": "Dominate farming, manufacturing, and retail; $800M annual revenue within 30 years.",
        "goal_focus_type": "exclude",
        "goal_focus_categories": ["Beverage", "Pasta", "Spice"],
        "stock_market_enabled": False,
    },
    {
        "key": "VOGUE", "name": "Staying in Vogue",
        "goal": "Replace competitors as market leader in all relevant markets within 30 years.",
        "goal_focus_type": "include_only",
        "goal_focus_categories": ["Apparel", "Cosmetics", "Jewelry", "Optical Products"],
        "stock_market_enabled": False,
    },
]

# Gameset ground truth, determined by extracting each scenario's .SCN save-game file
# (from the CapPlus.gog original CD image) and counting embedded product-name strings
# that are unique to one gameset's product catalog. Cross-validated against the 10
# scenarios whose text already gave an unambiguous category match -- 10/10 agreement.
SCN_GAMESET = {
    "DRAGON": "Standard", "ASIAN": "Standard", "ITALY": "Standard", "SILICON": "Standard",
    "TECHNO": "Standard", "DILEMMA": "Standard", "ENTREPRE": "Standard", "GLOBAL": "Standard",
    "RACETIME": "Alternative", "SPAIN": "Alternative", "UK": "Alternative", "VOGUE": "Alternative",
    "BERLIN": "Alternative", "BRINK": "Alternative", "JAPAN": "Alternative", "LATECOME": "Alternative",
    "UNDER": "Food & Beverage", "VERTICAL": "Food & Beverage", "FORTIFY": "Food & Beverage", "ROUGH": "Food & Beverage",
}

for s in SCENARIOS:
    s["gameset"] = SCN_GAMESET[s["key"]]
    s["gameset_inference_basis"] = "confirmed via embedded product-name strings in the scenario's .SCN save file"

for s in SCENARIOS:
    print(f"{s['name']:35s} -> {s['gameset'] or 'UNKNOWN':16s} ({s['gameset_inference_basis']})")

with open("/tmp/scenarios.json", "w") as f:
    json.dump(SCENARIOS, f, indent=2)

unverified = [s["name"] for s in SCENARIOS if "UNVERIFIED" in s["gameset_inference_basis"]]
print(f"\n{len(unverified)} scenarios have gameset assigned by default assumption, not confirmed:")
for u in unverified:
    print(" -", u)
