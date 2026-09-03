I verified the operational pieces this plan depends on (Etsy access from India, payments, print fulfilment, ephemeris licensing) before writing it. Here is the ground-up path.

## The one decision that makes everything small

Build a single computational core and give it a neutral, astronomical brand, not an astrological one. The core is an ephemeris engine that can render the sky for any date and place with a sidereal nakshatra ring and produce a kundali. Everything you eventually sell is a different face of that one object: a wall print, a compatibility card, a verification render for the Mahabharata debate, the Bethlehem sky in December. The interpretation, when it comes, is sold under a named human's name, not the brand's. That single split (brand = the sky as a historical record; person = the reading) dissolves your hard-wall problem, keeps Christian buyers comfortable, and means you never build two hubs.

Concretely, the engine is Swiss Ephemeris plus a few hundred lines of code: planetary longitudes with Lahiri ayanamsa, nakshatra and pada, the Ashtakoota arithmetic, and an SVG renderer. Licensing is a real decision, not a footnote: it's dual-licensed under either the AGPL or a professional license, and the choice must be made before any public service using it goes live; the professional license is a one-time CHF 750. Offline generation of images for print orders raises no issue; the public calculator in Stage 2 does, and I'd resolve it by open-sourcing the engine under AGPL, because that also becomes your authority asset later.

## Stage 0: the engine and three pictures (weeks 1–2, under ₹5,000)

Register the domain. Build the engine locally (a weekend with an AI coding tool if you code in Python; ₹15–30K on Upwork if you don't). Produce exactly three renders and nothing else:

1. A wedding-night sky over a named city with the nakshatra ring, in a palette that reads Indian (Pichwai indigo and gold, not Etsy-generic navy).
2. A six-panel plate: the same ephemeris, the same verse constraints, the sky on each proposed Mahabharata war date (5561, 3105, 3067, 1478, 1198 BCE, and the 3138 traditional date), side by side.
3. The sky over Jerusalem for the 7 BCE Jupiter–Saturn triple conjunction.

Render 1 is your product. Render 2 is your calling card in the history community and costs nothing to post. Render 3 waits until November. Register a sole proprietorship and get a GSTIN now, because Stage 1 needs it and your CA will take two weeks.

## Stage 1: first money on borrowed traffic (weeks 2–8, ₹20–30K)

Do not build a website. Open an Etsy shop. Sellers in India can open new shops, but only for international sales; there's a one-time $10 setup fee, you must verify a GSTIN, and payouts run through Payoneer, with payment processing at 5% plus ₹25. That export-only rule is a gift: it forces you onto the diaspora buyer who pays in dollars.

List three things. A personalized nakshatra sky print (wedding night or anniversary), a janma-nakshatra birth print for newborns that includes the naming syllables for the pada (grandparents in New Jersey buy this), and a digital-download version at $12–15. Digital items can be bought from any region except India. Fulfil physical orders through Gelato, which produces locally in 32 countries and integrates with Etsy, so a Chicago order prints in the US and you never touch inventory. Personalization is manual at first: buyer enters date, time, place; you render; you push the file to the print order. At 10–30 orders a month that's an evening's work.

Pricing and margin, roughly: $49 unframed, $89–119 framed; cost of goods plus domestic shipping around $15–18; Etsy fees around 12% (more if an offsite ad triggers); net $20–27 a print. Spend $3–5 a day on Etsy ads for the first six weeks. Order one sample for photos.

What you're really buying here isn't margin. It's three things you can't get any other way: reviews (the first trust asset), proof that anyone pays for the nakshatra angle, and order data that tells you what people commemorate and where they live. Gate: 10 sales and 5 reviews at 4.8+ inside 60 days of listing. Miss it and you've learned for ₹25K that this audience won't pay for artefacts, which redirects everything after.

## Stage 2: the forwardable card (weeks 6–12, ₹5–10K)

Now the first thing on your own domain, and it's one page. A compatibility calculator whose output isn't a score but a 1080×1350 image card built to be forwarded on WhatsApp to the parents: the guna total, each koota, the doshas, and which cancellations apply, with your URL on it. WhatsApp forwarding is how Indian families actually deliberate a match; the card is the growth loop, and it costs nothing per user.

The one feature that makes it forwardable and that nobody has: a birth-time uncertainty band. Most Indian birth times are approximate, and the moon changes nakshatra every day or so. Show how the score moves across ±30 minutes. "It's 26, not 18, if the time was 5:40" is a sentence people send to their mothers. It is also the doorway to the product in Stage 3.

Put two fake doors on the results page: "Get the full PDF with cancellations (₹299)" and "Ask a named astrologer to review this match." Both lead to a waitlist and an email field. You are counting clicks, not building. Seed the calculator in three places: r/arrangedmarriage and similar threads, NRI matrimony Facebook groups, and a short Reel showing the band move. Email is your list; WhatsApp is the distribution surface, not the database. Gate: 1,000 results in 30 days, a share rate above 20%, and a waitlist of 100 on the astrologer door. If the PDF door beats the astrologer door by a wide margin, run a real ₹299 pre-sale before building it; if not, kill the PDF for good.

## Stage 3: the practitioner and the dispute product (months 3–5, no cash)

If you're the astrologer, this stage happens inside Stage 1 as a fourth Etsy listing (a signed marriage-timing reading, $99–149, three-day delivery) and you skip recruitment. If you're not, the Stage 2 waitlist is your recruitment pitch. Find one astrologer with a small Instagram following and no product pipeline, and offer 60% of revenue for reading and signing; you own the funnel, the engine, the delivery, and the customer.

Launch one product: the guna and manglik second opinion. The customer uploads the family astrologer's verdict or the other app's report plus hospital birth records; the practitioner recalculates with the band, documents every applicable cancellation, and writes a respectful two-page letter the couple can hand to the parents. ₹2,999 in India, $79 abroad, five-day delivery, capped at 20 a month so scarcity is real. Payments: Razorpay for domestic, and for international either the Etsy shop or a merchant-of-record like Paddle, which is the legal seller on every transaction and handles VAT and sales tax for you (Dodo Payments is a cheaper Indian-founded equivalent at 4% plus $0.40 versus Paddle's 5% plus $0.50). Don't plan around Stripe: it's invite-only in India. Gate: 10 paid readings in the first 30 days, that's ₹30K gross, with a follow-on rate above 20% (a second reading, a print, a referral). This is the first month you have a business rather than a shop.

## Stage 4: muhurta for the people who actually schedule weddings (months 4–8, ₹5K)

The pain isn't finding a muhurta; the family priest does that. The pain is that the venue only has Saturday 4 p.m., the priest's window is 4 a.m. Tuesday, and nobody will write down a compromise the family can accept. Produce a free "Wedding muhurta calendar 2027" for US, UK, and Canadian time zones (the engine does it in an hour) and cold-email 50 South Asian wedding planners abroad. Sell two things: a per-couple "best window inside your venue slot" document at $150–300, signed by the practitioner, and a planner subscription for the calendar plus priority turnaround. Your Stage 1 order data tells you which cities to email first. Gate: five calls and two paying planners from the first 50 emails.

## Stage 5: sky-history as media, not as a hub (months 6–12, ₹10–20K)

Only now do you spend on what you love, and you spend it on video and code, not articles. The six-panel Mahabharata plate becomes a screen-recorded channel: "let's actually check the sky" for each claim, calm, tool-driven, no adjudication needed because the renders do the arguing. Open-source the verification tool on GitHub, with every dating claim encoded as machine-checkable constraints; that's the citation asset AI can't absorb, and it satisfies the AGPL. In November, list the Bethlehem print on Etsy under the astronomy framing. The ebook exists only if the channel shows demand by month 9. Gate: 1,000 subscribers from the first 10 videos in 90 days, otherwise it's a hobby channel and you say so.

## Stage 6: the content site, last

Articles, AdSense, and the year-ahead report were the first things in your original plan. They're the last here, and two of them never arrive: the year-ahead report and the bundle are dead. Write evergreen pages only where a tool already lives, put AdSense on sky-history pages no earlier than month nine, and treat it as a floor.

## What realistic looks like

Cash to month 8: under ₹1 lakh, all of it recoverable in Stage 1 learning even if you stop. If every gate passes, a plausible month 12 is 30–60 prints ($750–1,500 net), 15–30 readings (₹45K–2.4 lakh depending on mix), and three to six planners, so somewhere between ₹1.5 and 4 lakh a month gross. Those are my estimates, not benchmarks, and the readings line is where the range lives. If the gates fail, you're out for less than the cost of the website you were going to build first.

Don't do in the first 90 days: a blog, AdSense, an app, the Christian hub, the ebook, any PDF product without a pre-sale. Do this week: get the GSTIN started, install the ephemeris, and render the wedding sky over the first city you'd sell to.