import LegalPageLayout, {
  LegalBulletList as BulletList,
  LegalContactCard,
  LegalSection as Section,
} from "../components/legal/LegalPageLayout";

export default function PrivacyPage() {
  return (
    <LegalPageLayout
      title="Privacy Policy"
      description="This Privacy Policy explains how Dmpolin Connect collects, uses, stores, protects, and shares personal information when you use our website, support channels, internet services, and payment systems."
      effectiveDate="April 1, 2026"
      quickStats={[
        {
          label: "What We Collect",
          value:
            "We may collect contact, account, payment, support, device, and service usage information needed to operate our services.",
        },
        {
          label: "Why We Use It",
          value:
            "We use personal information to provide services, manage accounts, process payments, offer support, improve systems, and meet legal obligations.",
        },
        {
          label: "Your Rights",
          value:
            "You may contact us to ask questions, request corrections, raise concerns, or exercise applicable privacy rights.",
        },
      ]}
      topLinks={[
        { to: "/", label: "Back to Home" },
        { to: "/terms", label: "View Terms", variant: "secondary" },
      ]}
    >
      <Section id="overview" title="1. Overview">
        <p>
          This Privacy Policy explains how Dmpolin Connect handles personal
          information in connection with our website, internet services, support
          interactions, payment channels, and related business operations.
        </p>
        <p>
          We are committed to handling personal data responsibly, lawfully, and
          in a way that supports trust, service delivery, and operational security.
        </p>
      </Section>

      <Section id="information-collected" title="2. Information We Collect">
        <p>Depending on how you interact with us, we may collect:</p>
        <BulletList
          items={[
            "Name, phone number, email address, and location details",
            "Account details such as account number, package, subscription, or service status",
            "Payment records including transaction references and related billing details",
            "Support communications, complaints, and service history",
            "Technical or device-related information needed to operate and secure services",
            "Information you provide through website forms, support channels, or onboarding processes",
          ]}
        />
      </Section>

      <Section id="how-we-use" title="3. How We Use Information">
        <p>We may use personal information to:</p>
        <BulletList
          items={[
            "Provide, activate, maintain, and support internet services",
            "Process payments, renewals, reconnections, and billing-related actions",
            "Respond to support requests, complaints, and abuse reports",
            "Improve service delivery, network management, and customer experience",
            "Detect fraud, prevent misuse, and protect our systems",
            "Comply with legal, regulatory, and operational obligations",
          ]}
        />
      </Section>

      <Section id="sharing" title="4. How Information May Be Shared">
        <p>
          Dmpolin Connect does not sell personal data as a business model.
          However, we may share information where reasonably necessary with:
        </p>
        <BulletList
          items={[
            "Payment providers and related transaction service partners",
            "Technical vendors or service providers supporting our operations",
            "Regulators, law enforcement, courts, or other authorities where required by law",
            "Professional advisers or auditors where legitimately necessary",
          ]}
        />
      </Section>

      <Section id="retention" title="5. Data Retention">
        <p>
          We retain information for as long as reasonably necessary to provide
          services, maintain records, resolve disputes, enforce agreements,
          support network operations, and comply with legal or regulatory obligations.
        </p>
      </Section>

      <Section id="security" title="6. Data Security">
        <p>
          We take reasonable technical and organizational steps to protect
          personal information against unauthorized access, misuse, loss,
          alteration, or disclosure.
        </p>
        <p>
          No system can be guaranteed completely secure, but we work to protect
          our services, payment workflows, and customer records in a commercially
          reasonable manner.
        </p>
      </Section>

      <Section id="customer-rights" title="7. Your Privacy Rights">
        <p>Depending on applicable law, you may have the right to:</p>
        <BulletList
          items={[
            "Request access to personal information we hold about you",
            "Request correction of inaccurate or outdated information",
            "Raise concerns about how your information is being used",
            "Ask questions about our privacy practices",
          ]}
        />
      </Section>

      <Section id="cookies" title="8. Website and Technical Data">
        <p>
          Our website and technical systems may collect limited technical data
          needed for security, diagnostics, analytics, performance, and service
          continuity.
        </p>
      </Section>

      <Section id="changes" title="9. Changes to This Policy">
        <p>
          We may update this Privacy Policy from time to time to reflect changes
          in law, operations, services, or internal practices.
        </p>
        <p>
          The latest version will be published on our website, and continued use
          of our services after updates take effect constitutes acceptance of the
          revised policy.
        </p>
      </Section>

      <Section id="contact" title="10. Contact Us">
        <p>
          If you have questions or concerns about this Privacy Policy, please
          contact Dmpolin Connect.
        </p>
        <LegalContactCard />
      </Section>
    </LegalPageLayout>
  );
}