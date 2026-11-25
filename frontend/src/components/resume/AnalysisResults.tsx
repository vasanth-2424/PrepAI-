import type { ResumeAnalysis } from '../../types';

interface AnalysisResultsProps {
  analysis: ResumeAnalysis;
}

function Section({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h3>
      {items.length > 0 ? (
        <ul className="space-y-1 text-slate-200">
          {items.map((item) => (
            <li key={item} className="flex items-start gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">{emptyText}</p>
      )}
    </div>
  );
}

export function AnalysisResults({ analysis }: AnalysisResultsProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 sm:p-8">
      <h2 className="mb-6 text-xl font-bold text-white">Resume Analysis</h2>

      <div className="mb-6">
        <p className="text-sm text-slate-400">Candidate Name</p>
        <p className="text-lg font-semibold text-white">
          {analysis.name || 'Not detected'}
        </p>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Skills
        </h3>
        {analysis.skills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {analysis.skills.map((skill) => (
              <span
                key={skill}
                className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-sm text-indigo-200"
              >
                {skill}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No skills detected in the resume.</p>
        )}
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <Section title="Projects" items={analysis.projects} emptyText="No projects listed." />
        <Section title="Education" items={analysis.education} emptyText="No education listed." />
        <Section title="Experience" items={analysis.experience} emptyText="No experience listed." />
        <Section
          title="Certifications"
          items={analysis.certifications}
          emptyText="No certifications listed."
        />
      </div>
    </section>
  );
}
