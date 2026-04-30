import { describe, expect, it } from "vitest";

import {
  getReviewStatusColor,
  getReviewStatusLabel,
  requiresManualReview,
} from "../src/components/results/resultPresentation";

const completedReviewRequired = {
  processingStatus: "completed",
  systemDecision: "review_required",
  duplicateFlag: false,
};

describe("result presentation", () => {
  it.each([
    ["approved", "green"],
    ["rejected", "red"],
  ])("treats legacy %s review status as terminal", (reviewStatus, color) => {
    const params = {
      ...completedReviewRequired,
      reviewStatus,
    };

    expect(requiresManualReview(params)).toBe(false);
    expect(getReviewStatusLabel(params)).not.toBe("待人工确认");
    expect(getReviewStatusColor(params)).toBe(color);
  });
});
