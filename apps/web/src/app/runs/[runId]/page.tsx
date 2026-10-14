import React, { Suspense } from "react";
import { RunDetailContent } from "./RunDetailContent";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

export default function RunDetailPage() {
  return (
    <Suspense fallback={<LoadingSkeleton rows={4} />}>
      <RunDetailContent />
    </Suspense>
  );
}
