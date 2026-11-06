"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import clsx from "clsx";
import type { ProductImage } from "@/lib/types";
import { ProductThumb } from "./product-card";

export function Gallery({ images, title, categorySlug }: { images: ProductImage[]; title: string; categorySlug: string }) {
  const [i, setI] = useState(0);
  if (images.length === 0) {
    return (
      <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-canvas">
        <ProductThumb src={null} alt={title} categorySlug={categorySlug} />
      </div>
    );
  }
  const go = (d: number) => setI((x) => (x + d + images.length) % images.length);
  return (
    <div className="space-y-2">
      <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-black/90 sm:aspect-[16/9]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={images[i].url} alt={`${title} — photo ${i + 1} of ${images.length}`} className="size-full object-contain" fetchPriority="high" />
        {images.length > 1 && (
          <>
            <button onClick={() => go(-1)} aria-label="Previous photo" className="absolute left-3 top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-ink shadow-md transition hover:bg-white">
              <ChevronLeft className="size-6" />
            </button>
            <button onClick={() => go(1)} aria-label="Next photo" className="absolute right-3 top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-ink shadow-md transition hover:bg-white">
              <ChevronRight className="size-6" />
            </button>
            <span className="absolute bottom-3 left-3 rounded-md bg-black/70 px-2 py-1 text-xs font-semibold text-white">{i + 1}/{images.length}</span>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="grid grid-cols-4 gap-2">
          {images.map((im, idx) => (
            <button key={im.id} onClick={() => setI(idx)} aria-label={`Show photo ${idx + 1}`}
              className={clsx("aspect-[4/3] overflow-hidden rounded-lg ring-2 transition", idx === i ? "ring-brand-600" : "ring-transparent opacity-75 hover:opacity-100")}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={im.thumb_url} alt="" loading="lazy" className="size-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
