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
      <div className="card aspect-[4/3] overflow-hidden">
        <ProductThumb src={null} alt={title} categorySlug={categorySlug} />
      </div>
    );
  }
  const go = (d: number) => setI((x) => (x + d + images.length) % images.length);
  return (
    <div className="space-y-2">
      <div className="card relative aspect-[4/3] overflow-hidden bg-black/90">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={images[i].url} alt={`${title} — photo ${i + 1} of ${images.length}`} className="size-full object-contain" fetchPriority="high" />
        {images.length > 1 && (
          <>
            <button onClick={() => go(-1)} aria-label="Previous photo" className="absolute left-2 top-1/2 grid size-9 -translate-y-1/2 place-items-center rounded-full bg-white/85 shadow">
              <ChevronLeft className="size-5" />
            </button>
            <button onClick={() => go(1)} aria-label="Next photo" className="absolute right-2 top-1/2 grid size-9 -translate-y-1/2 place-items-center rounded-full bg-white/85 shadow">
              <ChevronRight className="size-5" />
            </button>
            <span className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">{i + 1}/{images.length}</span>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="scrollbar-none flex gap-2 overflow-x-auto">
          {images.map((im, idx) => (
            <button key={im.id} onClick={() => setI(idx)} aria-label={`Show photo ${idx + 1}`}
              className={clsx("size-16 shrink-0 overflow-hidden rounded-lg ring-2", idx === i ? "ring-brand-600" : "ring-transparent opacity-70")}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={im.thumb_url} alt="" loading="lazy" className="size-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
