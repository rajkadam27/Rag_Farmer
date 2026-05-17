"""
AI Scheme Eligibility Checker
Checks farmer eligibility for major Indian/Maharashtra government schemes.
Uses an embedded knowledge base - no external API needed.
"""
from utils.llm import get_gemini_response

# Comprehensive knowledge base of major schemes
SCHEME_KNOWLEDGE = """
MAJOR INDIAN GOVERNMENT SCHEMES FOR FARMERS (2024-25):

1. PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)
   - Amount: Rs. 6,000/year (Rs. 2,000 every 4 months) - Direct Bank Transfer
   - Eligibility: All landholding farmer families. Land must be in farmer's name.
   - Exclusions: Income Tax payers, government employees, pension >Rs.10,000/month
   - Apply: pmkisan.gov.in or nearest CSC center
   - Documents: Aadhaar, Bank Account, Land Records (7/12)

2. NAMO SHETKARI MAHA SAMMAN NIDHI (Maharashtra Specific)
   - Amount: Additional Rs. 6,000/year (Rs. 2,000 every 4 months) - ON TOP of PM-Kisan
   - Eligibility: Maharashtra farmers who are already enrolled in PM-Kisan
   - Total benefit: Rs. 12,000/year when combined with PM-Kisan
   - Apply: Automatic if registered in PM-Kisan in Maharashtra

3. PRADHAN MANTRI FASAL BIMA YOJANA (PMFBY) - Crop Insurance
   - Benefit: Insurance coverage for crop loss due to natural calamities, pests
   - Premium: Kharif: 2%, Rabi: 1.5%, Commercial/Horticulture: 5% of sum insured
   - Coverage: Up to Rs. 30,000-50,000 per acre depending on crop
   - Eligibility: All farmers including tenant farmers and sharecroppers
   - Apply: Through nearest bank, CSC or insurance company before sowing

4. KISAN CREDIT CARD (KCC)
   - Amount: Up to Rs. 3 lakh loan at 4% interest (government subsidized)
   - Eligibility: All farmers, sharecroppers, tenant farmers, Self Help Groups
   - Repayment: Flexible - repay after crop harvest
   - Apply: Nearest bank (SBI, Bank of Maharashtra, etc.)
   - Documents: Land records, Aadhaar, photo

5. SOIL HEALTH CARD SCHEME
   - Benefit: FREE soil testing + personalized fertilizer recommendation card
   - Eligibility: All farmers in India - completely free
   - Frequency: Every 2 years
   - Apply: Nearest KVK (Krishi Vigyan Kendra) or Agriculture office

6. PM KISAN MAAN DHAN YOJANA (Pension Scheme)
   - Benefit: Rs. 3,000/month pension after age 60
   - Eligibility: Age 18-40, small/marginal farmers (<2 hectares land)
   - Premium: Rs. 55-200/month (based on entry age) - very affordable
   - Apply: Nearest CSC center with Aadhaar and bank account

7. MUKHYAMANTRI SAUR KRISHI PUMP YOJANA (Maharashtra Solar Pump)
   - Benefit: Solar water pump (3 HP or 5 HP) at 90-95% subsidy (pay only 5-10%)
   - Eligibility: Maharashtra farmers with agricultural connection or no electricity
   - Priority: SC/ST farmers get higher priority; no agricultural connection: 100% free
   - Apply: mahadiscom.in or agriculture department

8. ATAL SOLAR KRUSHI PUMP YOJANA (Maharashtra)
   - Similar to above, 3HP pump for Rs. 10,000 (only 10% cost), 5HP for Rs. 15,000
   - Eligibility: Farmers with farmland, no grid connection preferred

9. PRADHAN MANTRI KRISHI SINCHAI YOJANA (PMKSY) - Drip/Sprinkler Irrigation
   - Subsidy: 45-55% subsidy on drip/sprinkler irrigation system
   - SC/ST/Small Farmers: Up to 55% subsidy
   - Others: 45% subsidy
   - Eligibility: All farmers with minimum 0.5 acre land
   - Apply: Agriculture department or at mahaportal.gov.in

10. ATMA NIRBHAR SHETKARI SCHEME (Maharashtra)
    - Emergency crop loan up to Rs. 50,000 at 0% interest for distressed farmers
    - Eligibility: Maharashtra farmers facing crop failure or drought

11. NATIONAL AGRICULTURE MARKET (e-NAM)
    - Benefit: Sell crops ONLINE at best price across India - no middlemen
    - Eligibility: All farmers
    - Register: enam.gov.in - free registration

12. PARAMPARAGAT KRISHI VIKAS YOJANA (PKVY) - Organic Farming
    - Benefit: Rs. 50,000/hectare over 3 years for switching to organic farming
    - Eligibility: Farmer groups (minimum 50 farmers, 50 acres)
    - Apply: Through agriculture department

13. RASHTRIYA KRISHI VIKAS YOJANA (RKVY)
    - Infrastructure grants for cold storage, warehouses, processing units
    - Eligibility: Farmer groups and FPOs

14. Maharashtra SHETKARI AAPATTI VIMA YOJANA (Accident Insurance)
    - Rs. 2 lakh accident insurance for ALL Maharashtra farmers - completely FREE
    - Eligibility: All farmers in Maharashtra aged 10-75 years
    - No application needed - automatic for all farmers

15. INTEREST SUBVENTION SCHEME (Short-term Crop Loan)
    - Crop loans up to Rs. 3 lakh at only 4% interest per annum
    - If repaid on time: additional 3% rebate = effectively only 4% interest
    - Eligibility: All farmers taking crop loans from banks
"""

ELIGIBILITY_PROMPT = """You are a government scheme expert for Maharashtra farmers, India.
A farmer has given their profile details. Check their eligibility against these schemes and give personalized advice.

FARMER PROFILE:
{profile}

AVAILABLE SCHEMES KNOWLEDGE BASE:
{schemes}

RESPOND IN THIS LANGUAGE: {language}

Provide the response in a rich, structured format suitable for a dashboard. Use Markdown for highlighting.

Format the response EXACTLY like this:

# Farmer Scheme Dashboard: {name}

## ✅ Schemes You Are DEFINITELY Eligible For:
[For each scheme, use a bullet point, bold the name, and mention amount clearly]
- **Scheme Name**: Rs. X,XXX - [Reason & 1-step how to apply]

## ⚠️ Schemes You MIGHT Be Eligible For (Verify Once):
[List with potential benefits]

## ❌ Why Some Schemes Don't Apply:
[Reasoning for age/land size mismatch]

## 💡 Most Important Action:
**[Action Name]**: [Description]

## 📞 Helplines:
- [List 3 main helplines]

Keep language simple and farmer-friendly.
"""

def check_eligibility(profile: dict, language: str = "Marathi") -> str:
    """Check scheme eligibility based on farmer profile and requested language."""
    profile_text = f"""
    Name: {profile.get('name', 'Farmer')}
    Age: {profile.get('age', 'Not provided')} years
    State: {profile.get('state', 'Maharashtra')}
    Land Size: {profile.get('land_size', 'Not provided')} acres
    Crops Grown: {profile.get('crops', 'Not provided')}
    Category: {profile.get('category', 'General')}
    Annual Income: ₹{profile.get('income', 'Not provided')}
    Has Bank Account: {profile.get('has_bank', 'Yes')}
    Has Aadhaar: {profile.get('has_aadhaar', 'Yes')}
    Already Getting PM-Kisan: {profile.get('pm_kisan', 'No')}
    Irrigation Type: {profile.get('irrigation', 'Not provided')}
    """
    
    lang_map = {
        "Marathi": "Marathi (मराठी)",
        "Hindi": "Hindi (हिंदी)",
        "English": "English"
    }
    
    prompt = ELIGIBILITY_PROMPT.format(
        profile=profile_text,
        schemes=SCHEME_KNOWLEDGE,
        language=lang_map.get(language, "Marathi"),
        name=profile.get('name', 'Farmer')
    )
    
    return get_gemini_response(prompt)
