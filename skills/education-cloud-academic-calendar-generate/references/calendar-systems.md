# Academic Calendar Systems

## Standard Calendar Systems

### Semester System (Most Common)

**Structure**: 3 terms per academic year

| Term | Typical Duration | Common Start Months |
|------|------------------|---------------------|
| Fall | August - December | August, September |
| Spring | January - May | January |
| Summer | May/June - August | May, June |

**Characteristics**:
- Fall and Spring are full-length terms (14-16 weeks)
- Summer is typically shorter (6-12 weeks) and often divided into sessions
- Summer Session 1: First half of summer (e.g., May-July)
- Summer Session 2: Second half of summer (e.g., June-August)
- Sessions may overlap by 1-2 weeks to allow accelerated pathways

**Education Cloud Mapping**:
- Create 1 Academic Year record
- Create 3 Term records (Fall, Spring, Summer)
- Create 2+ Session records for Summer (if subdivided)

---

### Quarter System

**Structure**: 4 terms per academic year

| Term | Typical Duration | Common Start Months |
|------|------------------|---------------------|
| Fall | September - December | September, October |
| Winter | January - March | January |
| Spring | March/April - June | March, April |
| Summer | June - August | June, July |

**Characteristics**:
- All terms roughly equal length (10-11 weeks)
- Summer quarter is often optional or lighter enrollment
- Less common in community colleges, more common in research universities

**Education Cloud Mapping**:
- Create 1 Academic Year record
- Create 4 Term records (Fall, Winter, Spring, Summer)
- Sessions within quarters are rare

---

### Trimester System

**Structure**: 3 terms per academic year (equal length)

| Term | Typical Duration | Common Start Months |
|------|------------------|---------------------|
| Fall | August/September - December | August, September |
| Winter | January - April | January |
| Spring | April/May - August | April, May |

**Characteristics**:
- All terms are roughly equal length (12-14 weeks)
- Unlike semester/quarter systems, trimester terms typically use Fall/Winter/Spring — there is usually no separate Summer term, since the three terms already span the full year
- Less common than semester or quarter systems
- Often used in international institutions or specialized programs
- Term naming and boundaries vary by institution — always follow the user's stated term names and dates literally rather than forcing this table's months onto them

**Education Cloud Mapping**:
- Create 1 Academic Year record
- Create 3 Term records (Fall, Winter, Spring), each with a valid `Season` picklist value — never a combined value like "Winter/Spring"

---

## Non-Standard Patterns

### Block/Module System

Some institutions use intensive block schedules where terms are further subdivided into modules (e.g., 7-week half-terms).

**Education Cloud Mapping**:
- Create Term for the full block period
- Create Session for each module within the block

### Rolling Start

Some online or continuing education programs have rolling starts (new cohorts every month).

**Education Cloud Mapping**:
- Create Term for each cohort start period
- Name terms by cohort (e.g., "January 2026 Cohort")

---

## Determining Calendar System from User Input

### Indicators of Semester System

User mentions:
- "Fall, Spring, and Summer"
- "Two main terms plus summer"
- "14-week Fall semester"
- "Summer Session 1 and 2"

### Indicators of Quarter System

User mentions:
- "Four quarters"
- "Fall, Winter, Spring, Summer"
- "10-week terms"
- "We run on quarters"

### Indicators of Trimester System

User mentions:
- "Three equal terms"
- "12-week terms"
- "We use trimesters"

### Ambiguous Cases

If user says only:
- "Fall and Spring" → Likely semester (missing Summer)
- "Three terms" → Could be semester or trimester (ask for term lengths)
- "Four terms" → Likely quarter (but could be semester with Winter intersession)

**Resolution**: Ask clarifying question: "Does your institution use a semester (Fall/Spring/Summer) or quarter (Fall/Winter/Spring/Summer) calendar system?"
