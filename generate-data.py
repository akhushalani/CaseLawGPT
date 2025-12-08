#!/usr/bin/env python3
"""Generate realistic synthetic legal case data for CaseLawGPT demo."""
from __future__ import annotations

import json
import random
from pathlib import Path
from src.config import RAW_DATA_DIR, ensure_directories

# Realistic legal building blocks
FIRST_NAMES = ["James", "Michael", "Robert", "John", "David", "William", "Richard", "Joseph", "Thomas", "Christopher", "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen", "Martinez", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Wilson"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott", "Hill"]
COMPANIES = ["Acme Corp", "Global Industries", "Pacific Holdings", "Eastern Manufacturing", "Western Resources", "National Services", "American Products", "United Technologies", "Continental Systems", "Metropolitan Group"]
GOVT_ENTITIES = ["United States", "State of California", "State of New York", "State of Texas", "City of Los Angeles", "County of Cook", "State of Florida", "Commonwealth of Massachusetts"]

COURTS = [
    ("Supreme Court of the United States", "U.S.", "United States"),
    ("United States Court of Appeals for the Ninth Circuit", "F.3d", "United States"),
    ("United States Court of Appeals for the Second Circuit", "F.3d", "United States"),
    ("United States Court of Appeals for the Fifth Circuit", "F.3d", "United States"),
    ("United States Court of Appeals for the Seventh Circuit", "F.3d", "United States"),
    ("United States District Court for the Southern District of New York", "F. Supp. 3d", "United States"),
    ("United States District Court for the Central District of California", "F. Supp. 3d", "United States"),
    ("Supreme Court of California", "Cal.4th", "California"),
    ("Supreme Court of New York", "N.Y.3d", "New York"),
    ("Supreme Court of Texas", "S.W.3d", "Texas"),
]

LEGAL_TOPICS = {
    "fourth_amendment": {
        "keywords": ["Fourth Amendment", "search and seizure", "warrant", "probable cause", "exclusionary rule"],
        "opinions": [
            """The Fourth Amendment protects individuals against unreasonable searches and seizures by the government. In this case, we must determine whether the warrantless search of the defendant's vehicle falls within the automobile exception to the warrant requirement. Under Carroll v. United States, 267 U.S. 132 (1925), law enforcement officers may search a vehicle without a warrant if they have probable cause to believe it contains contraband or evidence of a crime. The rationale for this exception rests on the reduced expectation of privacy in vehicles and their inherent mobility. Here, the officer observed what appeared to be contraband in plain view through the vehicle's window, establishing probable cause. The subsequent search was therefore constitutionally permissible, and the evidence obtained is admissible. We affirm the lower court's denial of the motion to suppress.""",
            """We hold that the search conducted in this case violated the Fourth Amendment's prohibition against unreasonable searches. The government argues that the defendant consented to the search, but the totality of circumstances indicates otherwise. Consent must be voluntary, and the presence of multiple armed officers, the late hour, and the officer's commanding tone all suggest coercion rather than free choice. See Schneckloth v. Bustamonte, 412 U.S. 218 (1973). Furthermore, the government bears the burden of proving voluntary consent, which it has failed to meet. The evidence obtained must be suppressed under the exclusionary rule established in Mapp v. Ohio, 367 U.S. 643 (1961). The judgment below is reversed.""",
            """The question presented is whether a police officer's use of a thermal imaging device to detect heat patterns emanating from a private home constitutes a search within the meaning of the Fourth Amendment. We hold that it does. When the government uses technology not in general public use to explore details of a home that would previously have been unknowable without physical intrusion, the surveillance is a search and presumptively unreasonable without a warrant. See Kyllo v. United States, 533 U.S. 27 (2001). The sanctity of the home lies at the core of the Fourth Amendment's protections, and we decline to permit technology to erode these fundamental rights. The warrant requirement is not an inconvenience to be avoided but a constitutional safeguard to be honored.""",
        ]
    },
    "qualified_immunity": {
        "keywords": ["qualified immunity", "clearly established", "constitutional right", "Section 1983", "civil rights"],
        "opinions": [
            """The doctrine of qualified immunity shields government officials from civil liability unless their conduct violates clearly established statutory or constitutional rights of which a reasonable person would have known. Harlow v. Fitzgerald, 457 U.S. 800 (1982). In analyzing qualified immunity claims, courts engage in a two-step inquiry: whether the facts alleged show the officer's conduct violated a constitutional right, and whether that right was clearly established at the time. Saucier v. Katz, 533 U.S. 194 (2001). A right is clearly established when existing precedent places the constitutional question beyond debate. Here, although the officer's use of force was significant, we cannot say that every reasonable officer would have known such force was excessive under these specific circumstances. We therefore hold that the defendant is entitled to qualified immunity.""",
            """We deny qualified immunity in this case because the constitutional violation was clear. The right to be free from excessive force during an arrest has been established for decades. When an individual poses no immediate threat, is not actively resisting, and the underlying offense is minor, the use of significant force is objectively unreasonable. Graham v. Connor, 490 U.S. 386 (1989). The defendant officer tased a compliant suspect who was already handcuffed and posed no threat. No reasonable officer could have believed this conduct was lawful. The plaintiff's Section 1983 claim may proceed.""",
            """Qualified immunity balances two important interests: the need to hold public officials accountable when they exercise power irresponsibly and the need to shield officials from harassment, distraction, and liability when they perform their duties reasonably. The qualified immunity standard is forgiving and protects all but the plainly incompetent or those who knowingly violate the law. Here, we find that officers acted reasonably given the information available to them at the time, even if hindsight suggests a different course of action would have been preferable. Officials are not required to err on the side of caution at the risk of their own safety.""",
        ]
    },
    "due_process": {
        "keywords": ["due process", "Fourteenth Amendment", "procedural", "substantive", "liberty interest"],
        "opinions": [
            """The Due Process Clause of the Fourteenth Amendment provides that no State shall deprive any person of life, liberty, or property without due process of law. This clause has both procedural and substantive components. Procedural due process requires that the government provide adequate notice and a meaningful opportunity to be heard before depriving an individual of a protected interest. Mathews v. Eldridge, 424 U.S. 319 (1976). In determining what process is due, courts balance the private interest affected, the risk of erroneous deprivation and value of additional safeguards, and the government's interest. Here, the state terminated the plaintiff's benefits without prior notice or hearing, violating fundamental procedural due process requirements.""",
            """Substantive due process protects fundamental rights that are deeply rooted in this nation's history and tradition and implicit in the concept of ordered liberty. Washington v. Glucksberg, 521 U.S. 702 (1997). When government action infringes upon a fundamental right, courts apply strict scrutiny, requiring the government to demonstrate that the action is narrowly tailored to serve a compelling state interest. The right at issue here, while important, does not rise to the level of a fundamental right warranting heightened protection. We therefore apply rational basis review and find that the challenged regulation bears a reasonable relationship to a legitimate governmental objective.""",
            """The guarantee of due process ensures fair treatment through the normal judicial system as a matter of right. This includes the right to notice of charges, the right to confront witnesses, and the right to present a defense. In criminal proceedings, these protections are at their apex. The defendant was denied the opportunity to cross-examine the key witness against him, a violation of both due process and the Confrontation Clause. Such errors are not harmless when the witness's testimony was central to the prosecution's case. We reverse the conviction and remand for a new trial.""",
        ]
    },
    "contract": {
        "keywords": ["contract", "breach", "consideration", "damages", "performance"],
        "opinions": [
            """A valid contract requires offer, acceptance, consideration, and mutual assent. The plaintiff alleges that defendant breached a contract for the sale of goods by failing to deliver conforming merchandise. Under the Uniform Commercial Code, which governs this transaction, a seller must tender delivery of goods that conform to the contract in every respect. UCC § 2-601. The evidence establishes that defendant delivered goods materially different from those specified in the agreement. Plaintiff properly rejected the nonconforming goods and is entitled to cover damages under UCC § 2-712, representing the difference between the cost of cover and the contract price. Judgment for plaintiff in the amount of $150,000.""",
            """The parol evidence rule prohibits the admission of extrinsic evidence to contradict, vary, or add to the terms of an integrated written agreement. Here, the parties executed a detailed written contract containing a merger clause stating that the writing constitutes the entire agreement between them. The defendant seeks to introduce evidence of prior oral negotiations to alter the contract's terms. We hold this evidence inadmissible. The contract is unambiguous on its face, and the parties clearly intended it to be a complete integration of their agreement. The written terms control, and the plaintiff is entitled to enforce them as written.""",
            """Under the doctrine of anticipatory repudiation, when one party unequivocally indicates it will not perform its contractual obligations, the non-breaching party may treat the contract as breached and seek immediate remedies. The defendant's letter stating it would not deliver the contracted goods under any circumstances constitutes a clear and unequivocal repudiation. Plaintiff was entitled to await performance for a reasonable time or resort immediately to any remedy for breach. Having elected to seek cover, plaintiff may recover the difference between cover price and contract price, plus incidental and consequential damages.""",
        ]
    },
    "first_amendment": {
        "keywords": ["First Amendment", "free speech", "freedom of expression", "content-based", "public forum"],
        "opinions": [
            """The First Amendment, applicable to the states through the Fourteenth Amendment, provides that government shall make no law abridging the freedom of speech. Content-based restrictions on speech are presumptively unconstitutional and subject to strict scrutiny. Reed v. Town of Gilbert, 576 U.S. 155 (2015). The ordinance at issue here restricts speech based on its subject matter, treating political speech differently from commercial speech. This is a content-based distinction that cannot survive strict scrutiny. The government has not demonstrated that the restriction serves a compelling interest or that it is narrowly tailored to achieve that interest. The ordinance is unconstitutional.""",
            """Not all speech receives equal First Amendment protection. Commercial speech, while protected, may be regulated more freely than political or artistic expression. Under Central Hudson Gas & Electric Corp. v. Public Service Commission, 447 U.S. 557 (1980), regulations of commercial speech must concern lawful activity, directly advance a substantial governmental interest, and be no more extensive than necessary. The regulation before us restricts advertising for lawful products and services. While the government has a substantial interest in preventing consumer deception, the blanket prohibition here is more extensive than necessary to serve that interest. The regulation fails Central Hudson and must be struck down.""",
            """Public forum doctrine distinguishes among three categories of government property for First Amendment purposes: traditional public forums, designated public forums, and nonpublic forums. Streets and parks are quintessential traditional public forums where the government's ability to restrict speech is most limited. The city's prohibition on all demonstrations in the public park is a content-neutral time, place, and manner restriction. Such restrictions are valid if they are narrowly tailored to serve a significant governmental interest and leave open ample alternative channels of communication. The total ban here fails this test because it does not leave open adequate alternatives for expression.""",
        ]
    },
    "negligence": {
        "keywords": ["negligence", "duty of care", "breach", "causation", "damages", "reasonable person"],
        "opinions": [
            """To establish negligence, a plaintiff must prove four elements: duty, breach, causation, and damages. The defendant owed plaintiff a duty of reasonable care as a business invitee on defendant's premises. Premises liability law requires property owners to maintain their property in a reasonably safe condition and to warn of known hazards. The evidence shows defendant knew of the dangerous condition for several weeks but failed to repair it or warn visitors. This constitutes a breach of the duty of care. The breach was both the actual and proximate cause of plaintiff's injuries, which resulted in medical expenses and lost wages. We find for the plaintiff.""",
            """The doctrine of comparative negligence allocates fault among parties based on their respective degrees of responsibility for the harm. Under our state's modified comparative fault system, a plaintiff may recover damages only if the plaintiff's fault does not exceed that of the defendant. Here, the jury found plaintiff 40% at fault for failing to observe an obvious hazard and defendant 60% at fault for creating the dangerous condition. Because plaintiff's fault does not exceed defendant's, plaintiff may recover, but the award is reduced by plaintiff's percentage of fault. The judgment of $100,000 is reduced to $60,000.""",
            """Proximate cause requires that the defendant's negligence be a substantial factor in bringing about the harm and that the harm be a reasonably foreseeable consequence of the negligence. Unforeseeable intervening causes may break the chain of causation. Here, while defendant was negligent in leaving equipment unsecured, the criminal acts of a third party that led to plaintiff's injuries were not reasonably foreseeable. Criminal conduct by third parties is generally considered a superseding cause that relieves the original tortfeasor of liability. We hold that defendant's negligence was not the proximate cause of plaintiff's injuries and enter judgment for defendant.""",
        ]
    },
    "criminal_procedure": {
        "keywords": ["Miranda", "right to counsel", "self-incrimination", "confession", "interrogation"],
        "opinions": [
            """Miranda v. Arizona, 384 U.S. 436 (1966), requires that prior to custodial interrogation, suspects must be informed of their right to remain silent and their right to counsel. Statements obtained in violation of Miranda are inadmissible in the prosecution's case-in-chief. The question here is whether the defendant was in custody when questioned. Custody exists when a reasonable person in the suspect's position would not feel free to terminate the encounter and leave. Considering the totality of circumstances, including the location of the interrogation, the number of officers present, and the length of questioning, we conclude defendant was in custody. The statements obtained without Miranda warnings must be suppressed.""",
            """The Sixth Amendment guarantees the accused the right to assistance of counsel for his defense. This right attaches once adversary judicial proceedings have commenced against the defendant. Once attached, the police may not deliberately elicit statements from the defendant outside the presence of counsel. The government argues that the defendant initiated the conversation with the informant placed in his cell. However, the government's deliberate creation of this situation to circumvent the defendant's Sixth Amendment rights cannot be condoned. The statements obtained through the informant are inadmissible. The conviction is reversed.""",
            """A confession must be voluntary to be admissible under the Due Process Clause. Voluntariness is determined by examining the totality of circumstances, including the defendant's characteristics and the conditions of interrogation. Factors such as the defendant's age, education, intelligence, and whether he was advised of his rights are relevant. Here, the defendant was interrogated for eighteen hours without food or rest, was repeatedly told resistance was futile, and was denied access to family members. Under these coercive circumstances, the confession cannot be considered the product of free will. The confession is suppressed, and the case is remanded for further proceedings.""",
        ]
    },
    "statutory_interpretation": {
        "keywords": ["statutory interpretation", "legislative intent", "plain meaning", "ambiguity", "canon"],
        "opinions": [
            """When interpreting a statute, we begin with the plain language. If the statutory text is unambiguous, our inquiry ends there, for clear statutory language must be given effect. The statute at issue provides that employers shall not discriminate on the basis of sex. The term sex unambiguously refers to biological distinctions between male and female. The plaintiff argues for a broader interpretation encompassing gender identity, but such an expansion would require legislative action. We are not at liberty to rewrite statutes under the guise of interpretation. The plain meaning controls, and plaintiff's claim must be dismissed.""",
            """When statutory language is ambiguous, we look to legislative history and the statute's purpose to discern congressional intent. The disputed term admits of multiple reasonable interpretations. The legislative history reveals that Congress intended the provision to be interpreted broadly to effectuate its remedial purpose. Committee reports explicitly state that the term should encompass the conduct at issue here. We therefore interpret the statute in accordance with this expressed intent. To hold otherwise would frustrate Congress's clear objective in enacting this legislation.""",
            """The rule against surplusage counsels that courts should give effect to every word of a statute and avoid interpretations that render provisions superfluous. The government's reading would make subsection (b) entirely redundant with subsection (a). This cannot be what Congress intended. We must presume that Congress acts intentionally when it includes particular language in one section but omits it from another. Each provision must be given independent effect. Under a proper reading of the statute that honors this principle, the defendant's conduct falls outside the prohibition.""",
        ]
    },
}

def generate_party_name() -> str:
    """Generate a realistic party name."""
    roll = random.random()
    if roll < 0.3:
        return f"{random.choice(LAST_NAMES)}"
    elif roll < 0.5:
        return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    elif roll < 0.7:
        return random.choice(COMPANIES)
    else:
        return random.choice(GOVT_ENTITIES)

def generate_case(case_num: int) -> dict:
    """Generate a single synthetic case."""
    court_name, reporter, jurisdiction = random.choice(COURTS)
    topic = random.choice(list(LEGAL_TOPICS.keys()))
    topic_data = LEGAL_TOPICS[topic]
    
    year = random.randint(1960, 2024)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    
    plaintiff = generate_party_name()
    defendant = generate_party_name()
    while defendant == plaintiff:
        defendant = generate_party_name()
    
    volume = random.randint(1, 600)
    page = random.randint(1, 1500)
    
    # Generate opinions
    main_opinion = random.choice(topic_data["opinions"])
    opinions = [{"type": "majority", "text": main_opinion}]
    
    # Sometimes add concurrence or dissent
    if random.random() < 0.3:
        other_topic = random.choice(list(LEGAL_TOPICS.keys()))
        dissent = random.choice(LEGAL_TOPICS[other_topic]["opinions"])
        dissent = f"I respectfully dissent. {dissent}"
        opinions.append({"type": "dissenting", "text": dissent})
    
    if random.random() < 0.2:
        concur = "I concur in the judgment but write separately to emphasize the narrow scope of today's holding. " + random.choice(topic_data["opinions"])[:500]
        opinions.append({"type": "concurring", "text": concur})
    
    return {
        "id": f"case-{case_num:06d}",
        "name": f"{plaintiff} v. {defendant}",
        "name_abbreviation": f"{plaintiff.split()[-1]} v. {defendant.split()[-1]}",
        "citations": [{"cite": f"{volume} {reporter} {page}"}],
        "court": {"name": court_name},
        "jurisdiction": {"name": jurisdiction},
        "decision_date": f"{year}-{month:02d}-{day:02d}",
        "casebody": {"opinions": opinions}
    }

def generate_dataset(n_cases: int = 200, output_dir: Path = RAW_DATA_DIR):
    """Generate full synthetic dataset."""
    ensure_directories()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {n_cases} synthetic cases...")
    
    for i in range(n_cases):
        case = generate_case(i + 1)
        filepath = output_dir / f"{case['id']}.json"
        with open(filepath, 'w') as f:
            json.dump(case, f, indent=2)
        
        if (i + 1) % 50 == 0:
            print(f"  Generated {i + 1}/{n_cases} cases...")
    
    print(f"Done! {n_cases} cases saved to {output_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic legal case data")
    parser.add_argument("--n-cases", type=int, default=200, help="Number of cases to generate")
    args = parser.parse_args()
    generate_dataset(args.n_cases)
