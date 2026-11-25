export function Footer() {
  return (
    <footer className="border-t border-slate-800/60 py-8">
      <div className="mx-auto max-w-6xl px-6 text-center text-sm text-slate-500">
        <p>&copy; {new Date().getFullYear()} PrepAI. Stage 2 — Authentication &amp; Database.</p>
      </div>
    </footer>
  );
}
