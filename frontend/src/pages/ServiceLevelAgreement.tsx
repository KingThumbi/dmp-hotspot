import LegalPageLayout, {
  LegalBulletList as BulletList,
  LegalContactCard,
  LegalSection as Section,
} from "../components/legal/LegalPageLayout";

const supportChannels = [
  "Customer support phone and official support contacts",
  "Email support via support@dmpolinconnect.co.ke",
  "Official website contact forms or approved customer care channels",
];

const exclusions = [
  "Power failures, vandalism, theft, fiber cuts, or damage beyond our direct control",
  "Customer device faults, router misconfiguration, damaged cables, or unsafe premises",
  "Interruptions caused by third-party upstream providers, mobile money providers, or utility failures",
  "Scheduled maintenance communicated in advance where reasonably possible",
  "Force majeure events including severe weather, fire, civil unrest, or government action",
  "Suspension arising from non-payment, policy violations, suspected fraud, or lawful enforcement requirements",
];

const customerResponsibilities = [
  "Paying for services on time to avoid interruption or suspension",
  "Providing accurate account, location, and contact information",
  "Maintaining safe access to customer premises and installed equipment",
  "Ensuring customer-owned devices, routers, and internal cabling are functional and secure",
  "Promptly reporting faults, outages, or suspected misuse of service",
  "Using the service in accordance with our Terms, Privacy Policy, Refund Policy, and Acceptable Use Policy",
];

export default function ServiceLevelAgreementPage() {
  return (
    <LegalPageLayout
      title="Service Level Agreement"
      description="This Service Level Agreement explains Dmpolin Connect’s general service commitments, support approach, customer responsibilities, and the practical limits that affect service availability and restoration."
      effectiveDate="April 1, 2026"
      quickStats={[
        {
          label: "Scope",
          value:
            "Applies to residential, hotspot, and standard business internet services unless a separate written contract says otherwise.",
        },
        {
          label: "Support Approach",
          value:
            "We aim to acknowledge issues within a reasonable time and restore service as quickly as practical based on the fault type and operating conditions.",
        },
        {
          label: "Availability Basis",
          value:
            "Service is provided on a best-effort basis and may be affected by maintenance, upstream incidents, environmental conditions, or third-party dependencies.",
        },
      ]}
      topLinks={[
        { to: "/", label: "Back to Home" },
        { to: "/refund-policy", label: "View Refund Policy", variant: "secondary" },
      ]}
    >
      <Section id="overview" title="1. Overview">
        <p>
          This Service Level Agreement, or SLA, describes the general service
          standards and support expectations for Dmpolin Connect services.
        </p>
        <p>
          It is intended to give customers a clear understanding of how service
          is delivered, how faults are handled, and what operational realities
          can affect restoration, speed, and continuity.
        </p>
      </Section>

      <Section id="services-covered" title="2. Services Covered">
        <p>This SLA generally applies to:</p>
        <BulletList
          items={[
            "Residential internet subscriptions",
            "Hotspot internet access services",
            "Standard business internet services where no separate custom agreement exists",
            "Basic support related to connectivity, payments, and account service status",
          ]}
        />
      </Section>

      <Section id="commitment" title="3. Service Commitment">
        <p>
          Dmpolin Connect aims to deliver internet service with reasonable care,
          operational diligence, and practical responsiveness.
        </p>
        <p>We work to:</p>
        <BulletList
          items={[
            "Maintain stable and secure network operations",
            "Monitor and address service interruptions within reasonable limits",
            "Restore verified service faults as quickly as practical",
            "Communicate major outages or planned maintenance where reasonably possible",
            "Promote fair, stable, and reliable service for all users",
          ]}
        />
      </Section>

      <Section id="availability" title="4. Service Availability">
        <p>
          Dmpolin Connect strives to keep services available on an ongoing basis.
          However, internet service is not immune to outages, degradation,
          latency, or interruptions.
        </p>
        <p>
          Actual speeds and performance may vary depending on network load,
          device capability, signal quality, Wi-Fi conditions, location,
          third-party dependencies, and other technical or environmental factors.
        </p>
      </Section>

      <Section id="support-reporting" title="5. Support and Fault Reporting">
        <p>
          Customers should report service issues through official support
          channels. These may include:
        </p>
        <BulletList items={supportChannels} />
        <p>
          To help speed up troubleshooting, customers should provide enough
          information to identify the affected service, confirm payment status
          where relevant, describe the issue clearly, and indicate when the
          problem began.
        </p>
      </Section>

      <Section id="restoration" title="6. Response and Restoration">
        <p>
          Dmpolin Connect aims to acknowledge and begin reviewing reported
          service issues within a reasonable time after receipt.
        </p>
        <p>
          Restoration time depends on the nature of the problem, availability of
          technicians and materials, accessibility of the site, safety
          considerations, the scale of the outage, and whether the fault lies
          within our infrastructure or in third-party systems.
        </p>
        <p>
          Priority is generally given to major outages, core network incidents,
          multi-customer faults, and verified payment-related reconnection issues.
        </p>
      </Section>

      <Section id="maintenance" title="7. Planned Maintenance">
        <p>
          We may carry out scheduled or emergency maintenance, upgrades,
          migrations, reconfiguration, or repair work to improve stability,
          security, or capacity.
        </p>
        <p>
          Where reasonably possible, notice of significant maintenance will be
          communicated in advance. Emergency work may sometimes be performed
          immediately without prior notice if required to protect the network or
          restore service.
        </p>
      </Section>

      <Section id="exclusions" title="8. Exclusions and Limitations">
        <p>This SLA may not apply, or may be limited, in situations involving:</p>
        <BulletList items={exclusions} />
      </Section>

      <Section id="customer-responsibilities" title="9. Customer Responsibilities">
        <p>Customers help support reliable service by:</p>
        <BulletList items={customerResponsibilities} />
      </Section>

      <Section id="suspension" title="10. Suspension and Reconnection">
        <p>
          Dmpolin Connect may suspend or restrict service where payment is
          overdue, security concerns exist, misuse is suspected, policy
          violations occur, or suspension is required by law or operational need.
        </p>
        <p>
          For prepaid services, reconnection generally follows receipt,
          verification, and successful application of a valid payment to the
          affected account, subject to normal technical and operational checks.
        </p>
      </Section>

      <Section id="credits-refunds" title="11. Credits and Refunds">
        <p>
          Unless specifically stated in a separate written agreement, this SLA
          does not create an automatic entitlement to service credits, prorated
          compensation, or refunds for every outage, delay, or slowdown.
        </p>
        <p>
          Any goodwill adjustment, account credit, or refund remains subject to
          the Refund Policy and the facts of the specific case.
        </p>
      </Section>

      <Section id="liability" title="12. Limitation of Liability">
        <p>
          To the extent permitted by law, Dmpolin Connect is not liable for
          indirect, incidental, consequential, or special losses resulting from
          service interruption, delayed restoration, data loss, lost business,
          lost revenue, or reliance on third-party systems.
        </p>
        <p>
          Where connectivity is business-critical, customers should maintain
          their own backups, power protection, device security, and continuity
          arrangements.
        </p>
      </Section>

      <Section id="changes" title="13. Changes to This SLA">
        <p>
          Dmpolin Connect may update this Service Level Agreement from time to
          time to reflect changes in services, operations, support practices,
          legal requirements, or network design.
        </p>
        <p>
          The latest version will be published on our website, and continued use
          of our services after updates take effect constitutes acceptance of the
          revised SLA.
        </p>
      </Section>

      <Section id="contact" title="14. Contact Us">
        <p>
          If you have questions about this Service Level Agreement or need
          service support, please contact Dmpolin Connect.
        </p>
        <LegalContactCard />
      </Section>
    </LegalPageLayout>
  );
}