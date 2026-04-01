import { Link } from "react-router-dom";

const prohibitedActivities = [
  {
    title: "Illegal activity",
    items: [
      "Engaging in fraud, theft, impersonation, deception, or identity misuse.",
      "Distributing unlawful content or using the service for unlawful purposes.",
      "Violating intellectual property rights belonging to others.",
      "Running scams, phishing campaigns, or other deceptive schemes.",
      "Accessing accounts, devices, systems, or data without authorization.",
    ],
  },
  {
    title: "Network abuse",
    items: [
      "Attempting to bypass authentication, security, or access controls.",
      "Interfering with or disrupting our network or another user’s service.",
      "Introducing malware, viruses, worms, trojans, or other harmful code.",
      "Performing denial-of-service attacks, flooding, port scanning, or malicious probing.",
      "Operating unauthorized services that negatively affect stability, security, or network performance.",
    ],
  },
  {
    title: "Abuse of communications",
    items: [
      "Sending spam or bulk unsolicited messages.",
      "Using our systems for harassment, threats, intimidation, or abuse.",
      "Distributing misleading, deceptive, or fraudulent communications.",
      "Misusing support channels, payment systems, SMS, or email services.",
    ],
  },
  {
    title: "Harmful or offensive use",
    items: [
      "Transmitting unlawful, abusive, hateful, defamatory, or harmful material.",
      "Using the service in a way that endangers others.",
      "Invading privacy or unlawfully collecting or processing personal data.",
    ],
  },
  {
    title: "Unauthorized resale or sharing",
    items: [
      "Reselling, redistributing, or sharing the service beyond your subscribed use without our written approval.",
      "Extending access to third parties in a way that breaches your package terms or undermines fair network use.",
    ],
  },
  {
    title: "Payment and account abuse",
    items: [
      "Providing false information during registration, support, or payment processes.",
      "Using stolen, unauthorized, or fraudulent payment details.",
      "Manipulating billing, package activation, suspension, reconnection, or usage systems.",
      "Attempting to reconnect suspended services without authorization.",
    ],
  },
];

const responsibilities = [
  "Keeping your login details, passwords, and account information secure.",
  "Ensuring your devices are protected against malware and unauthorized access.",
  "Ensuring all equipment connected through your account is used lawfully and responsibly.",
  "Notifying us promptly if you suspect fraud, account compromise, or unauthorized use.",
];

const enforcementActions = [
  "Issue a warning",
  "Restrict or limit access",
  "Suspend or disconnect service",
  "Block certain traffic or activity",
  "Cancel accounts or subscriptions",
  "Report suspected unlawful conduct to relevant authorities",
  "Take legal action where appropriate",
];

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-[0_10px_40px_rgba(0,0,0,0.25)] backdrop-blur-sm md:p-8"
    >
      <h2 className="text-xl font-bold tracking-tight text-white md:text-2xl">
        {title}
      </h2>
      <div className="mt-4 space-y-4 text-sm leading-7 text-slate-300 md:text-base">
        {children}
      </div>
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3">
          <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-yellow-400" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function AcceptableUsePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="relative overflow-hidden border-b border-yellow-500/10 bg-gradient-to-b from-[#000080] via-slate-950 to-slate-950">
        <div className="absolute inset-0">
          <div className="absolute left-1/2 top-0 h-64 w-64 -translate-x-1/2 rounded-full bg-yellow-400/10 blur-3xl" />
          <div className="absolute -left-12 top-24 h-48 w-48 rounded-full bg-blue-400/10 blur-3xl" />
          <div className="absolute bottom-0 right-0 h-56 w-56 rounded-full bg-yellow-300/10 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-5xl px-6 py-16 md:px-8 md:py-20">
          <div className="inline-flex items-center rounded-full border border-yellow-400/20 bg-yellow-400/10 px-4 py-1.5 text-sm font-medium text-yellow-300">
            Dmpolin Connect Legal
          </div>

          <h1 className="mt-6 max-w-3xl text-4xl font-black tracking-tight text-white md:text-5xl">
            Acceptable Use Policy
          </h1>

          <p className="mt-5 max-w-3xl text-base leading-8 text-slate-300 md:text-lg">
            This policy explains the rules for lawful, fair, secure, and
            responsible use of Dmpolin Connect’s internet services, website,
            payment channels, customer portals, support platforms, and related
            infrastructure.
          </p>

          <div className="mt-8 flex flex-wrap gap-3 text-sm">
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200">
              Effective Date: April 1, 2026
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200">
              Company: Dmpolin Connect
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200">
              Website: dmpolinconnect.co.ke
            </span>
          </div>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              to="/"
              className="inline-flex items-center justify-center rounded-2xl bg-yellow-400 px-5 py-3 font-semibold text-slate-950 transition hover:scale-[1.02] hover:bg-yellow-300"
            >
              Back to Home
            </Link>
            <Link
              to="/privacy"
              className="inline-flex items-center justify-center rounded-2xl border border-white/15 bg-white/5 px-5 py-3 font-semibold text-white transition hover:bg-white/10"
            >
              View Privacy Policy
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 py-10 md:px-8 md:py-14">
        <div className="grid gap-4 rounded-3xl border border-yellow-500/10 bg-gradient-to-r from-yellow-400/10 to-white/[0.03] p-5 md:grid-cols-3 md:p-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-yellow-300">
              Quick Summary
            </p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              Use the service lawfully, protect your account, avoid abuse, and
              do not disrupt other users or our network.
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-yellow-300">
              Applies To
            </p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              Residential customers, hotspot users, business customers, website
              visitors, account holders, and anyone using systems connected to
              our network.
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-yellow-300">
              Enforcement
            </p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              Violations may result in warnings, restrictions, suspension,
              disconnection, investigation, or legal reporting where necessary.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-16 md:px-8 md:pb-20">
        <div className="grid gap-6">
          <Section id="introduction" title="1. Introduction">
            <p>
              This Acceptable Use Policy governs how Dmpolin Connect services
              may be accessed and used. By using our website, internet services,
              payment channels, customer portals, support systems, or related
              infrastructure, you agree to use them responsibly and in
              compliance with this policy.
            </p>
            <p>
              Our goal is to maintain a safe, stable, reliable, and fair network
              environment for all users.
            </p>
          </Section>

          <Section id="purpose" title="2. Purpose of This Policy">
            <p>This policy is intended to:</p>
            <BulletList
              items={[
                "Protect the integrity, security, and reliability of our network and services.",
                "Promote fair usage of internet and digital resources.",
                "Prevent illegal, abusive, fraudulent, or harmful activity.",
                "Protect customers, staff, partners, infrastructure, and third parties.",
              ]}
            />
          </Section>

          <Section id="scope" title="3. Scope">
            <p>This policy applies to all users of Dmpolin Connect services, including:</p>
            <BulletList
              items={[
                "Residential customers",
                "Hotspot users",
                "Business customers",
                "Website visitors",
                "Account holders",
                "Anyone using equipment or systems connected to our network",
              ]}
            />
          </Section>

          <Section id="lawful-use" title="4. Lawful Use Only">
            <p>
              You must use our services only for lawful purposes and in
              compliance with applicable laws and regulations in Kenya and any
              other relevant jurisdiction.
            </p>
            <p>
              You may not use our services to commit, support, encourage, or
              facilitate unlawful activity of any kind.
            </p>
          </Section>

          <Section id="prohibited-activities" title="5. Prohibited Activities">
            <p>
              You may not use Dmpolin Connect services in any way that harms our
              business, our infrastructure, other users, or third parties.
            </p>

            <div className="mt-6 grid gap-5 md:grid-cols-2">
              {prohibitedActivities.map((group) => (
                <div
                  key={group.title}
                  className="rounded-2xl border border-white/10 bg-slate-900/70 p-5"
                >
                  <h3 className="text-base font-semibold text-yellow-300">
                    {group.title}
                  </h3>
                  <div className="mt-4">
                    <BulletList items={group.items} />
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section id="fair-use" title="6. Fair Use and Network Integrity">
            <p>
              To maintain reliable service for all users, Dmpolin Connect may
              take reasonable steps to manage network performance, protect
              infrastructure, and prevent abuse.
            </p>
            <p>You must not engage in activity that:</p>
            <BulletList
              items={[
                "Causes excessive strain on the network",
                "Degrades service quality for other users",
                "Unfairly consumes shared resources",
                "Interferes with our ability to operate, secure, or maintain services",
              ]}
            />
            <p>
              Where necessary, we may investigate unusual or excessive usage
              patterns and take corrective action to protect service quality and
              operational stability.
            </p>
          </Section>

          <Section
            id="customer-responsibility"
            title="7. Customer Equipment and Account Responsibility"
          >
            <p>You are responsible for:</p>
            <BulletList items={responsibilities} />
            <p>
              Any activity conducted through your account may be treated as your
              responsibility unless you promptly report compromise or
              unauthorized use and cooperate reasonably with any investigation.
            </p>
          </Section>

          <Section id="suspension" title="8. Suspension and Enforcement">
            <p>
              If we reasonably believe that you have violated this policy, we
              may act without prior notice where necessary to protect our
              network, customers, staff, systems, or business operations.
            </p>
            <p>Such action may include:</p>
            <BulletList items={enforcementActions} />
            <p>
              We may also cooperate with law enforcement, regulators, courts, or
              other lawful authorities where required or appropriate.
            </p>
          </Section>

          <Section id="investigations" title="9. Investigations">
            <p>
              Dmpolin Connect may investigate suspected violations of this
              policy. In doing so, we may review relevant technical records,
              account details, service logs, and incident reports to the extent
              reasonably necessary for security, compliance, operational
              integrity, fraud prevention, or legal obligations.
            </p>
          </Section>

          <Section id="third-party" title="10. Third-Party Services and Content">
            <p>
              Our services may enable access to third-party websites, platforms,
              applications, and services. Dmpolin Connect is not responsible for
              third-party systems, content, or practices.
            </p>
            <p>
              Users remain responsible for how they use third-party services
              through our network and for ensuring that such use remains lawful
              and appropriate.
            </p>
          </Section>

          <Section id="reporting" title="11. Reporting Abuse">
            <p>
              If you believe our services are being used in violation of this
              policy, please contact us with enough detail to help us
              investigate.
            </p>

            <div className="rounded-2xl border border-yellow-400/20 bg-yellow-400/10 p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-yellow-300">
                Contact
              </p>
              <a
                href="mailto:support@dmpolinconnect.co.ke"
                className="mt-2 inline-block text-lg font-semibold text-white hover:text-yellow-300"
              >
                support@dmpolinconnect.co.ke
              </a>

              <div className="mt-4">
                <p className="text-sm text-slate-300">
                  Where possible, include:
                </p>
                <div className="mt-3">
                  <BulletList
                    items={[
                      "A description of the incident",
                      "Date and time of occurrence",
                      "Affected service, user, or account",
                      "Any screenshots, logs, links, or supporting evidence",
                    ]}
                  />
                </div>
              </div>
            </div>
          </Section>

          <Section id="changes" title="12. Changes to This Policy">
            <p>
              We may update this Acceptable Use Policy from time to time to
              reflect service changes, legal obligations, regulatory
              requirements, operational practices, or security needs.
            </p>
            <p>
              The latest version will be published on our website. Continued use
              of our services after updates take effect constitutes acceptance
              of the revised policy.
            </p>
          </Section>

          <Section id="contact" title="13. Contact Us">
            <p>
              If you have any questions about this Acceptable Use Policy, please
              contact Dmpolin Connect.
            </p>

            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
              <p className="text-lg font-semibold text-white">Dmpolin Connect</p>
              <div className="mt-3 space-y-2 text-slate-300">
                <p>
                  Email:{" "}
                  <a
                    href="mailto:support@dmpolinconnect.co.ke"
                    className="text-yellow-300 hover:text-yellow-200"
                  >
                    support@dmpolinconnect.co.ke
                  </a>
                </p>
                <p>
                  Website:{" "}
                  <a
                    href="https://www.dmpolinconnect.co.ke"
                    className="text-yellow-300 hover:text-yellow-200"
                    target="_blank"
                    rel="noreferrer"
                  >
                    www.dmpolinconnect.co.ke
                  </a>
                </p>
              </div>
            </div>
          </Section>
        </div>
      </section>
    </main>
  );
}