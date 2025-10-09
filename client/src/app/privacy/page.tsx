export const metadata = {
  title: "Privacy Policy | Content Dreamer AI",
  description:
    "Read the Content Dreamer AI Privacy Policy to learn how we collect, use, and protect your information.",
};

export default function PrivacyPage() {
  const updated = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <main className="container mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        Privacy Policy
      </h1>
      <p className="mt-2 text-sm text-slate-500">Last updated: {updated}</p>

      <section className="prose prose-slate mt-8 dark:prose-invert">
        <p>
          This Privacy Policy explains how Content Dreamer AI (&quot;we&quot;, &quot;us&quot;, or
          &quot;our&quot;) collects, uses, and shares information about you when you use
          our websites, apps, and related services (collectively, the
          &quot;Services&quot;). By using the Services, you agree to the collection and
          use of information in accordance with this policy.
        </p>

        <h2>Information We Collect</h2>
        <p>We collect information in the following ways:</p>
        <ul>
          <li>
            Information you provide: account details, profile information,
            content you create or upload, and communications with us.
          </li>
          <li>
            Automatically collected information: device and usage data such as
            IP address, browser type, pages visited, referring URLs, and
            timestamps. We may use cookies and similar technologies for
            analytics and to improve your experience.
          </li>
          <li>
            Third-party sources: where permitted by law, we may receive
            information from partners and service providers to support our
            Services (e.g., authentication, payments, analytics, customer
            support).
          </li>
        </ul>

        <h2>How We Use Your Information</h2>
        <ul>
          <li>Provide, maintain, and improve the Services.</li>
          <li>Personalize features and content relevant to you.</li>
          <li>Process transactions and send related information.</li>
          <li>Communicate with you about updates, security, and support.</li>
          <li>Monitor and analyze trends, usage, and activities.</li>
          <li>Detect, investigate, and prevent security incidents or abuse.</li>
          <li>Comply with legal obligations and enforce our terms.</li>
        </ul>

        <h2>Legal Bases for Processing</h2>
        <p>
          Where applicable, we process personal data under legal bases such as
          performance of a contract, legitimate interests, consent, and
          compliance with legal obligations.
        </p>

        <h2>Sharing of Information</h2>
        <p>
          We may share information with service providers and partners who
          perform services on our behalf (e.g., cloud hosting, customer support,
          analytics, payments). We may also share information to comply with
          legal obligations, protect our rights, or in connection with a merger,
          acquisition, or sale of assets. We do not sell your personal
          information.
        </p>

        <h2>Data Retention</h2>
        <p>
          We retain information for as long as necessary to provide the
          Services, comply with legal obligations, resolve disputes, and enforce
          agreements. Retention periods vary depending on the type of data and
          our operational needs.
        </p>

        <h2>Your Rights</h2>
        <p>
          Depending on your location, you may have rights regarding your
          personal information, such as access, correction, deletion,
          restriction, objection, and portability. To exercise these rights,
          please contact us using the options in the footer (Contact) or via our
          official social channel at https://x.com/content_dreamer.
        </p>

        <h2>Cookies and Tracking</h2>
        <p>
          We use cookies and similar technologies to operate and improve the
          Services. You can manage cookies through your browser settings. Some
          features may not function properly without cookies.
        </p>

        <h2>Security</h2>
        <p>
          We implement reasonable administrative, technical, and physical
          safeguards designed to protect information. However, no method of
          transmission or storage is completely secure, and we cannot guarantee
          absolute security.
        </p>

        <h2>Children&apos;s Privacy</h2>
        <p>
          The Services are not directed to children under 13 (or the applicable
          age of digital consent in your jurisdiction). We do not knowingly
          collect personal information from children.
        </p>

        <h2>International Transfers</h2>
        <p>
          Your information may be transferred to and processed in countries
          other than your own. We take steps to ensure appropriate safeguards in
          accordance with applicable laws.
        </p>

        <h2>Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. We will revise
          the &quot;Last updated&quot; date above and, when appropriate, provide
          additional notice.
        </p>

        <h2>Contact Us</h2>
        <p>
          If you have questions about this Privacy Policy, please reach out via
          the Contact link in the footer or our official social channel at
          <a href="https://x.com/content_dreamer"> https://x.com/content_dreamer</a>.
        </p>
      </section>
    </main>
  );
}
