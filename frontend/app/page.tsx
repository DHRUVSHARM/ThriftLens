import { Search, Upload } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 lg:grid lg:grid-cols-[380px_1fr]">
        <section className="rounded-md border border-neutral-200 bg-white p-5 shadow-sm">
          <div className="mb-5">
            <p className="text-sm font-medium text-emerald-700">ThriftLens</p>
            <h1 className="mt-1 text-2xl font-semibold">Product research workbench</h1>
          </div>

          <div className="grid grid-cols-2 rounded-md border border-neutral-200 p-1 text-sm">
            <button className="flex items-center justify-center gap-2 rounded bg-neutral-950 px-3 py-2 text-white">
              <Upload size={16} aria-hidden="true" />
              Image
            </button>
            <button className="flex items-center justify-center gap-2 rounded px-3 py-2 text-neutral-700">
              <Search size={16} aria-hidden="true" />
              Text
            </button>
          </div>

          <div className="mt-5 flex min-h-48 items-center justify-center rounded-md border border-dashed border-neutral-300 bg-neutral-50 p-4 text-center text-sm text-neutral-600">
            Upload controls will land in the backend gateway slice.
          </div>
        </section>

        <section className="rounded-md border border-neutral-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4 border-b border-neutral-200 pb-4">
            <div>
              <p className="text-sm font-medium text-neutral-500">Status</p>
              <h2 className="text-xl font-semibold">Ready for research</h2>
            </div>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
              Sample mode ready
            </span>
          </div>

          <div className="grid min-h-96 place-items-center text-center text-neutral-500">
            <div>
              <p className="font-medium text-neutral-800">Runtime shell is ready.</p>
              <p className="mt-2 max-w-md text-sm">
                Job progress, product reference, source-backed matches, and grouped alternatives will fill this workbench as feature slices are implemented.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
