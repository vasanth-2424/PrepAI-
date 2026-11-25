const features = [
  {
    title: 'Resume Analysis',
    description:
      'Upload your resume and let AI extract skills, projects, and experience automatically.',
    icon: '📄',
  },
  {
    title: 'Personalized Questions',
    description:
      'Get interview questions tailored to your background, role, and target company.',
    icon: '💬',
  },
  {
    title: 'Mock Interviews',
    description:
      'Practice with realistic mock interviews and receive instant AI-powered evaluations.',
    icon: '🎯',
  },
  {
    title: 'Skill Gap & Roadmap',
    description:
      'Identify gaps in your skillset and follow a personalized learning roadmap to improve.',
    icon: '🗺️',
  },
];

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-6 py-16">
      <div className="mb-12 text-center">
        <h2 className="mb-3 text-3xl font-bold text-white">Everything You Need to Succeed</h2>
        <p className="text-slate-400">
          A complete interview preparation pipeline powered by AI.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 transition-colors hover:border-indigo-500/40"
          >
            <div className="mb-4 text-3xl">{feature.icon}</div>
            <h3 className="mb-2 font-semibold text-white">{feature.title}</h3>
            <p className="text-sm leading-relaxed text-slate-400">{feature.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
