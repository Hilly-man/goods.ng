import Link from "next/link";
import { SearchX } from "lucide-react";

export default function NotFound() {
  return (
    <div className="container-page grid min-h-[50vh] place-items-center py-12 text-center">
      <div>
        <SearchX className="mx-auto size-12 text-muted" />
        <h1 className="mt-3 text-2xl font-bold">We couldn&apos;t find that page</h1>
        <p className="mt-1 text-muted">The listing may have been sold or removed.</p>
        <Link href="/" className="mt-5 inline-block rounded-lg bg-brand-700 px-5 py-2.5 font-semibold text-white">Back to Goods.ng</Link>
      </div>
    </div>
  );
}
