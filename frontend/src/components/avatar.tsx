import clsx from "clsx";

/** Profile photo with an initials fallback (photos are optional). */
export function Avatar({ name, src, className }: { name: string; src?: string | null; className?: string }) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("") || "?";
  return (
    <span className={clsx("relative grid shrink-0 place-items-center overflow-hidden rounded-full bg-brand-100 font-bold text-brand-800", className)}>
      {src ? (
        // Avatars are already small server-encoded WebP thumbnails.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt="" className="size-full object-cover" />
      ) : (
        <span aria-hidden>{initials}</span>
      )}
    </span>
  );
}
