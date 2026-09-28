# Possible errors in vault notes, found while rewriting

The rewrite agents read every note closely, and they flag source problems here: errors, internal contradictions, garbled
text. **Nothing in the vault was changed.** Where a problem could be left out of the rewrite, it was. Where the checker
required a number to stay, the number stayed, sometimes with a hedge added ("by one reported count"). Each item is the
agent's reading, not a verified finding, so check it before editing the vault. Fixing a note marks its rewrite as stale,
and the next "all pending" run redoes it.

| Note | Problem | Source of the flag |
|---|---|---|
| `era/middle-paleolithic` (fact 4), `era/upper-paleolithic` (fact 3) | Stray "- " list marker glued mid-line runs two facts together | site-002/003 agents; a fix task was started separately |
| `place/mecca` (context) | Calls Mecca "the destination of the Hijra from Medina"; the Hijra went from Mecca to Medina (622), as the Medina note says | site-007 agent |
| `species/cassava` | Summary says "south-central Brazil", fact 1 says "west-central Brazil" (likely correct). Question 2 has a grammar slip ("How much do modern reliance…") | site-035 agent |
| `species/coffee` (fact 2) | States Pope Clement VIII's approval (1600) as fact, often considered apocryphal; first Venice coffeehouse usually dated 1645, not 1647 | site-035 agent |
| `species/anomalocaris` | Fact 1 says Chinese fossils were mostly moved to other genera, but the context still lists the Chengjiang Fossil Site | site-035 agent |
| `species/barley` (fact 5) | Odd ordering: "By about 2000 BCE… reaching Finland by about 4200 BCE" | site-035 agent |
| `place/nazca-lines` (context) | Puts Cusco and the Inca state "farther south"; Cusco is north-east of Nazca | site-037 agent |
| `species/sugarcane` (fact 3) | "By 1540 the island of Santa Catarina alone held about 800 sugar mills" is very likely wrong (island settled late 17th c.; Brazil had a few dozen mills c. 1570) | site-037 agent |
| `species/tobacco` (fact 2) | Francisco Hernández de Toledo bringing seeds to Spain in 1559 is doubtful (his New Spain expedition ran 1570 to 1577) | site-037 agent |
| `culture/ancestral-puebloans` (facts 3 and 4) | Implies the 1276 to 1299 drought explains Chaco Canyon's abandonment too; Chaco's decline began c. 1130 to 1150 | site-037 agent |
| `place/nan-madol` (context) | Ties Pohnpei's builders to the Polynesian settlement of the Pacific; Pohnpei was settled by non-Polynesian Austronesians | site-037 agent |
| `species/soybean` (facts 3 and 5) | Tempeh is from Java (Southeast Asia), not East Asia; commercial GM soy usually dated 1996, not 1995, and about 17% of US acreage by 1997, not 8% (from memory, unverified) | site-036 agent |
| `species/sheep` | Dates imply a 3,000 to 5,000-year gap between domestication and woolly sheep, but three fields call it "roughly two millennia" | site-036 agent |
| `species/rice` (context) | Says rice farming shaped the Yellow River region; Neolithic farming there was mainly millet, and rice came from the Yangtze | site-036 agent |
| `species/goat` (facts 1 and 2) | About 10,000 years ago vs. early sites at 8,000 to 9,000 years ago | site-036 agent |
| `culture/confucianism` (fact 1) | Places Confucius in the Warring States period; he lived (551 to 479 BCE) in the Spring and Autumn period | site-038 agent |
| `culture/celts` (fact 4) | "Rome attacked the Arverni in 125 BCE"; their defeat is usually dated 121 BCE (125 BCE began campaigns against another tribe) | site-038 agent |
| `culture/franks` (fact 2) | Clovis "had united the Frankish tribes by about 501"; more often given as c. 509 | site-038 agent |
