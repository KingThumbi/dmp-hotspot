import LegalPageLayout, {
  LegalBulletList as BulletList,
  LegalContactCard,
  LegalSection as Section,
} from "../components/legal/LegalPageLayout";

export default function RefundPolicyPage() {
  return (
    <LegalPageLayout
      title="Refund Policy"
      description="This policy explains how Dmpolin Connect handles refunds, reversals, billing corrections, and payment-related disputes for internet services and related charges."
      effectiveDate="April 1, 2026"
      quickStats={[
        {
          label: "Service Model",
          value:
            "Dmpolin Connect mainly provides prepaid internet services with payments applied toward activation or renewal.",
        },
        {
          label: "General Position",
          value:
            "Payments are generally non-refundable once service has been activated, provisioned, delivered, or substantially consumed.",
        },
        {
          label: "Possible Exceptions",
          value:
            "Refunds may be considered for duplicate payments, failed activation, billing errors, or qualifying provider-side service failures.",
        },
      ]}
      topLinks={[
        { to: "/", label: "Back to Home" },
        { to: "/acceptable-use", label: "View Acceptable Use", variant: "secondary" },
      ]}
    >
      <Section id="overview" title="1. Overview">
        <p>
          This Refund Policy explains when a payment made to Dmpolin Connect may
          qualify for a refund, reversal, correction, or account adjustment.
        </p>
        <p>
          Because our services are generally prepaid and provisioned digitally,
          refunds are limited and are assessed based on the payment record,
          service status, timing, and the specific facts of each case.
        </p>
      </Section>

      <Section id="general-rule" title="2. General Refund Rule">
        <p>
          Payments made for Dmpolin Connect services are generally non-refundable
          once the corresponding service has been successfully activated,
          delivered, renewed, or used.
        </p>
        <p>
          This includes cases where a package has already been applied to an
          account, access has been restored, or the customer has begun consuming
          service under the paid period.
        </p>
      </Section>

      <Section id="non-refundable" title="3. Non-Refundable Payments">
        <p>The following are generally not refundable:</p>
        <BulletList
          items={[
            "Payments for active or already delivered internet service",
            "Used hotspot sessions or residential subscription periods",
            "Partially consumed service periods",
            "Installation, setup, or site visit fees once work has been carried out",
            "Charges arising from customer error after service has already been provisioned",
          ]}
        />
      </Section>

      <Section id="eligible-cases" title="4. Cases That May Qualify for Review">
        <p>
          Refunds, reversals, or account credits may be considered in limited
          circumstances such as:
        </p>
        <BulletList
          items={[
            "Duplicate or accidental payments",
            "Failed activation where no service was actually delivered",
            "Incorrect billing caused by a system or administrative error",
            "A verified payment applied to the wrong account due to provider-side handling error",
            "Extended provider-side outage where service could not reasonably be delivered and no fair adjustment was made through another remedy",
          ]}
        />
      </Section>

      <Section id="mpesa" title="5. M-Pesa and Payment Reversals">
        <p>
          Many customer payments are processed through M-Pesa or related mobile
          payment workflows. Once a payment is confirmed as successful, it may be
          automatically matched to an account and applied toward activation,
          renewal, or reconnection.
        </p>
        <p>
          Where a reversal is requested, Dmpolin Connect may require transaction
          verification before any approval is considered.
        </p>
        <p>
          Reversal timing may also depend on Safaricom or the relevant payment
          provider’s own procedures, controls, and timelines.
        </p>
      </Section>

      <Section id="how-to-request" title="6. How to Request a Refund">
        <p>To request a refund or payment review, the customer should provide:</p>
        <BulletList
          items={[
            "The name and phone number used for payment",
            "The transaction reference, such as the M-Pesa code",
            "The account number, username, or affected service details",
            "A clear explanation of the issue",
            "Any supporting screenshots, messages, or receipts where available",
          ]}
        />
      </Section>

      <Section id="review-process" title="7. Review and Verification">
        <p>
          All refund requests are reviewed before any decision is made. Dmpolin
          Connect may verify payment logs, account activity, subscription status,
          support records, and related system events to determine whether the
          request qualifies.
        </p>
        <p>
          Approval is not automatic, and we reserve the right to deny a request
          where service was delivered, the claim is unsupported, or the payment
          is found to have been validly applied.
        </p>
      </Section>

      <Section id="timelines" title="8. Processing Timelines">
        <p>
          Where a refund or reversal is approved, processing is done within a
          reasonable period depending on the payment method, provider response,
          and verification outcome.
        </p>
        <BulletList
          items={[
            "M-Pesa reversals may take approximately 24 to 72 hours or longer depending on provider processing",
            "Other methods may depend on banking or payment provider timelines",
            "Complex disputes may require additional review time before a final outcome is communicated",
          ]}
        />
      </Section>

      <Section id="credits" title="9. Alternative Remedies">
        <p>
          In some cases, Dmpolin Connect may resolve an issue by applying an
          account credit, extending service time, correcting the billing record,
          or reprocessing activation instead of issuing a cash refund.
        </p>
        <p>
          The appropriate remedy will depend on the nature of the problem and
          whether the payment can still reasonably be used for the intended service.
        </p>
      </Section>

      <Section id="abuse" title="10. Abuse of This Policy">
        <p>
          Fraudulent or abusive refund claims are not allowed. Any attempt to
          manipulate payments, submit false claims, or misuse the review process
          may result in:
        </p>
        <BulletList
          items={[
            "Denial of the refund request",
            "Account suspension or termination",
            "Restriction of future payment privileges",
            "Further investigation or legal escalation where appropriate",
          ]}
        />
      </Section>

      <Section id="changes" title="11. Changes to This Policy">
        <p>
          Dmpolin Connect may update this Refund Policy from time to time to
          reflect service changes, payment processes, legal obligations, or
          operational requirements.
        </p>
        <p>
          The latest version will be published on our website, and continued use
          of our services after changes take effect constitutes acceptance of the
          updated policy.
        </p>
      </Section>

      <Section id="contact" title="12. Contact Us">
        <p>
          For refund questions, billing clarification, or payment disputes,
          please contact Dmpolin Connect.
        </p>
        <LegalContactCard />
      </Section>
    </LegalPageLayout>
  );
}