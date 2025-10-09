export const metadata = {
  title: "Terms of Service | Content Dreamer AI",
  description:
    "Read the Content Dreamer AI Terms of Service outlining your rights and responsibilities when using our Services.",
};

export default function TermsPage() {
  const updated = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <main className="container mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        Terms of Service
      </h1>
      <p className="mt-2 text-sm text-slate-500">Last updated: {updated}</p>

      <section className="prose prose-slate mt-8 dark:prose-invert">
        <p>
          These Terms of Service (the &quot;Terms&quot;) govern your access to and use of
          the websites, applications, and services provided by Content Dreamer AI
          (collectively, the &quot;Services&quot;). By accessing or using the Services,
          you agree to be bound by these Terms.
        </p>

        <h2>Eligibility</h2>
        <p>
          You must be at least 13 years of age (or the age of digital consent in
          your jurisdiction) to use the Services. If you are using the Services
          on behalf of an organization, you represent that you have the authority
          to bind that organization to these Terms.
        </p>

        <h2>Accounts and Security</h2>
        <ul>
          <li>You are responsible for maintaining the confidentiality of your account credentials.</li>
          <li>You are responsible for all activities that occur under your account.</li>
          <li>
            Notify us promptly of any unauthorized use of your account or any
            other security breach.
          </li>
        </ul>

        <h2>Acceptable Use</h2>
        <p>When using the Services, you agree not to:</p>
        <ul>
          <li>Violate any applicable laws or regulations.</li>
          <li>Infringe the rights of others, including intellectual property rights.</li>
          <li>Upload or transmit malicious code or content that is unlawful, harmful, or deceptive.</li>
          <li>Interfere with or disrupt the integrity or performance of the Services.</li>
          <li>Attempt to gain unauthorized access to the Services or related systems or networks.</li>
        </ul>

        <h2>User Content</h2>
        <p>
          You retain ownership of content you submit to the Services. By
          submitting content, you grant Content Dreamer AI a worldwide,
          non-exclusive, royalty-free license to use, reproduce, modify, adapt,
          publish, and display such content solely for the purpose of providing
          and improving the Services.
        </p>

        <h2>Intellectual Property</h2>
        <p>
          The Services, including all content, features, and functionality, are
          owned by or licensed to Content Dreamer AI and are protected by
          intellectual property laws. Except as expressly permitted, you may not
          copy, modify, distribute, sell, or lease any part of the Services.
        </p>

        <h2>Third-Party Services</h2>
        <p>
          The Services may integrate with or link to third-party services. Your
          use of such services is subject to their respective terms and privacy
          policies. We are not responsible for third-party services.
        </p>

        <h2>Payments and Subscriptions</h2>
        <p>
          If you purchase a subscription or paid features, you agree to the
          pricing, billing, and renewal terms presented at checkout. Taxes may
          apply. You can cancel at any time, but fees already paid are generally
          non-refundable unless required by law or stated otherwise.
        </p>

        <h2>Disclaimer of Warranties</h2>
        <p>
          THE SERVICES ARE PROVIDED ON AN &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; BASIS
          WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING
          IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
          PURPOSE, AND NON-INFRINGEMENT. WE DO NOT WARRANT THAT THE SERVICES
          WILL BE UNINTERRUPTED, ERROR-FREE, OR SECURE.
        </p>

        <h2>Limitation of Liability</h2>
        <p>
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, CONTENT DREAMER AI AND ITS
          AFFILIATES WILL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL,
          CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES
          ARISING OUT OF OR RELATED TO YOUR USE OF THE SERVICES.
        </p>

        <h2>Indemnification</h2>
        <p>
          You agree to indemnify and hold harmless Content Dreamer AI and its
          affiliates, officers, agents, and employees from any claims, damages,
          liabilities, and expenses arising out of your use of the Services or
          your violation of these Terms.
        </p>

        <h2>Termination</h2>
        <p>
          We may suspend or terminate your access to the Services at any time if
          we believe you have violated these Terms or if necessary to protect the
          Services or other users. Upon termination, your rights to use the
          Services will cease immediately.
        </p>

        <h2>Governing Law</h2>
        <p>
          These Terms are governed by and construed in accordance with the laws
          of the jurisdiction in which Content Dreamer AI operates, without
          regard to conflict of law principles.
        </p>

        <h2>Changes to These Terms</h2>
        <p>
          We may update these Terms from time to time. We will revise the &quot;Last
          updated&quot; date above and, when appropriate, provide additional notice.
        </p>

        <h2>Contact Us</h2>
        <p>
          If you have questions about these Terms, please reach out via the
          Contact link in the footer or our official social channel at
          <a href="https://x.com/content_dreamer"> https://x.com/content_dreamer</a>.
        </p>
      </section>
    </main>
  );
}
