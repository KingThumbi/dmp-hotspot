import LegalPageLayout, {
  LegalSection,
  LegalBulletList,
  LegalContactCard,
} from "../components/legal/LegalPageLayout";

export default function DataDeletion() {
  return (
    <LegalPageLayout
      badge="Dmpolin Connect Legal"
      title="Data Deletion Instructions"
      description="This page explains how customers can request deletion of their personal data from Dmpolin Connect systems and how such requests are handled."
      effectiveDate="2 April 2026"
      quickStats={[
        { label: "Request Channels", value: "Email, WhatsApp, Website Support" },
        { label: "Processing Time", value: "Typically 7–14 business days" },
        { label: "Applies To", value: "Customer data, subscriptions, communication logs" },
      ]}
    >
      <LegalSection id="request" title="1. How to Request Data Deletion">
        <p>
          Dmpolin Connect respects your privacy and your right to control your personal data.
          You may request deletion of your data at any time using any of the official channels below.
        </p>

        <LegalBulletList
          items={[
            "Email: support@dmpolinconnect.co.ke",
            "WhatsApp: +254780912362",
            "Website: Contact form on dmpolinconnect.co.ke",
          ]}
        />
      </LegalSection>

      <LegalSection id="information" title="2. Information Required">
        <p>
          To help us identify your account and prevent unauthorized deletion,
          please include the following details in your request:
        </p>

        <LegalBulletList
          items={[
            "Your full name",
            "Your registered phone number",
            "Your Dmpolin Connect account number (if available)",
            "Your service location (estate/apartment)",
            "A clear request stating you want your data deleted",
          ]}
        />
      </LegalSection>

      <LegalSection id="verification" title="3. Identity Verification">
        <p>
          Before processing your request, we may need to verify your identity.
          This helps prevent unauthorized deletion and protects your account.
        </p>

        <p>
          We may contact you through your registered phone number or email
          before proceeding.
        </p>
      </LegalSection>

      <LegalSection id="data-deleted" title="4. Data That May Be Deleted">
        <p>
          Depending on your request and applicable laws, we may delete or anonymize:
        </p>

        <LegalBulletList
          items={[
            "Customer profile information",
            "Phone number and contact details",
            "Subscription and service records",
            "Support and communication history",
            "Reminder and notification records (SMS and WhatsApp)",
          ]}
        />
      </LegalSection>

      <LegalSection id="data-retained" title="5. Data We May Retain">
        <p>
          Certain information may be retained where required for legal or operational reasons:
        </p>

        <LegalBulletList
          items={[
            "M-Pesa transaction and payment records",
            "Accounting and tax compliance data",
            "Fraud prevention and security logs",
            "Records required for dispute resolution",
          ]}
        />

        <p>
          Where full deletion is not possible, we will restrict processing and retain only what is necessary.
        </p>
      </LegalSection>

      <LegalSection id="timeline" title="6. Processing Timeline">
        <p>
          Once your request has been verified, Dmpolin Connect will process it within a reasonable timeframe,
          typically within 7 to 14 business days.
        </p>
      </LegalSection>

      <LegalSection id="third-party" title="7. Third-Party Platforms">
        <p>
          If you have communicated with us via third-party platforms such as WhatsApp,
          some data may also be retained by those platforms under their own policies.
        </p>

        <p>
          Deleting your data from Dmpolin Connect does not automatically remove data held by third-party providers.
        </p>
      </LegalSection>

      <LegalSection id="contact" title="8. Contact Us">
        <p>
          For any privacy-related inquiries or to request deletion of your data, please contact us:
        </p>

        <LegalContactCard />
      </LegalSection>
    </LegalPageLayout>
  );
}