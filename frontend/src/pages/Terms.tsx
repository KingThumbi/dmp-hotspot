import LegalPageLayout, {
  LegalBulletList as BulletList,
  LegalContactCard,
  LegalSection as Section,
} from "../components/legal/LegalPageLayout";

export default function TermsPage() {
  return (
    <LegalPageLayout
      title="Terms of Service"
      description="These Terms of Service govern the use of Dmpolin Connect’s website, internet services, support channels, payment systems, and related customer accounts."
      effectiveDate="April 1, 2026"
      quickStats={[
        {
          label: "Agreement",
          value:
            "Using our services means you agree to these terms and to the related legal policies published by Dmpolin Connect.",
        },
        {
          label: "Service Type",
          value:
            "Our services may include prepaid residential internet, hotspot access, business connectivity, website features, and customer support channels.",
        },
        {
          label: "Key Expectations",
          value:
            "Customers must provide accurate information, pay on time, use the service lawfully, and follow all applicable service policies.",
        },
      ]}
      topLinks={[
        { to: "/", label: "Back to Home" },
        { to: "/privacy", label: "View Privacy Policy", variant: "secondary" },
      ]}
    >
      <Section id="overview" title="1. Overview">
        <p>
          These Terms of Service govern access to and use of Dmpolin Connect’s
          services, including our website, internet connectivity services,
          support channels, customer-facing systems, and payment-related processes.
        </p>
        <p>
          By using our services, you agree to these Terms and to any related
          policies that apply to your use of the service.
        </p>
      </Section>

      <Section id="services" title="2. Services">
        <p>Dmpolin Connect may provide services such as:</p>
        <BulletList
          items={[
            "Residential internet subscriptions",
            "Hotspot internet access services",
            "Business internet connectivity",
            "Website inquiry, support, or customer account features",
            "Payment, renewal, and reconnection workflows",
          ]}
        />
      </Section>

      <Section id="customer-obligations" title="3. Customer Obligations">
        <p>Customers are expected to:</p>
        <BulletList
          items={[
            "Provide accurate registration, contact, and payment information",
            "Pay applicable charges on time",
            "Use the service lawfully and responsibly",
            "Protect account credentials and report unauthorized use promptly",
            "Comply with our Acceptable Use Policy and other related policies",
          ]}
        />
      </Section>

      <Section id="payments" title="4. Payments and Renewals">
        <p>
          Some Dmpolin Connect services operate on a prepaid basis. Service
          renewal, activation, suspension, and reconnection may depend on
          successful receipt and application of payment.
        </p>
        <p>
          Payment-related issues may require verification before service changes
          are processed.
        </p>
      </Section>

      <Section id="suspension" title="5. Suspension and Termination">
        <p>
          We may suspend, limit, or terminate service where payment is overdue,
          policies are violated, fraud is suspected, security risks arise, or
          action is required by law or operational necessity.
        </p>
      </Section>

      <Section id="service-performance" title="6. Service Performance">
        <p>
          Internet service is provided on a best-effort basis. Actual speed,
          continuity, and performance may vary depending on technical,
          environmental, device, and upstream provider conditions.
        </p>
      </Section>

      <Section id="liability" title="7. Limitation of Liability">
        <p>
          To the extent permitted by law, Dmpolin Connect is not liable for
          indirect, incidental, consequential, or special losses arising from
          service interruption, payment delays, third-party failures, or misuse
          of customer systems or credentials.
        </p>
      </Section>

      <Section id="policy-links" title="8. Related Policies">
        <p>These Terms should be read together with our related policies, including:</p>
        <BulletList
          items={[
            "Privacy Policy",
            "Acceptable Use Policy",
            "Refund Policy",
            "Service Level Agreement",
          ]}
        />
      </Section>

      <Section id="changes" title="9. Changes to These Terms">
        <p>
          Dmpolin Connect may update these Terms from time to time. The latest
          version will be published on our website, and continued use of the
          service after updates take effect constitutes acceptance of the revised terms.
        </p>
      </Section>

      <Section id="contact" title="10. Contact Us">
        <p>
          If you have questions about these Terms of Service, please contact
          Dmpolin Connect.
        </p>
        <LegalContactCard />
      </Section>
    </LegalPageLayout>
  );
}