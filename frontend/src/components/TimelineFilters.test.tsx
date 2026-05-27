import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TimelineFilters } from "./TimelineFilters";

describe("TimelineFilters", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces query changes before notifying the parent", async () => {
    vi.useFakeTimers();
    const onQueryChange = vi.fn();

    render(
      <TimelineFilters
        since=""
        until=""
        query=""
        eventTypes={[]}
        sourceEntityTypes={[]}
        answeredOnly={false}
        activePresetDays={null}
        hasActiveFilters={false}
        onSinceChange={vi.fn()}
        onUntilChange={vi.fn()}
        onQueryChange={onQueryChange}
        onEventTypeToggle={vi.fn()}
        onSourceTypeToggle={vi.fn()}
        onAnsweredOnlyChange={vi.fn()}
        onPresetSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );

    fireEvent.change(screen.getByRole("searchbox", { name: /search title or summary/i }), {
      target: { value: "planning" },
    });

    expect(onQueryChange).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(349);
    });
    expect(onQueryChange).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(onQueryChange).toHaveBeenCalledWith("planning");
  });

  it("wires filter actions and shows the active filter summary when collapsed", async () => {
    const onAnsweredOnlyChange = vi.fn();
    const onPresetSelect = vi.fn();
    const onClear = vi.fn();

    render(
      <TimelineFilters
        since="2026-05-01"
        until="2026-05-10"
        query="housing"
        eventTypes={["question_answered"]}
        sourceEntityTypes={["question"]}
        answeredOnly={true}
        activePresetDays={30}
        hasActiveFilters={true}
        resultCount={4}
        onSinceChange={vi.fn()}
        onUntilChange={vi.fn()}
        onQueryChange={vi.fn()}
        onEventTypeToggle={vi.fn()}
        onSourceTypeToggle={vi.fn()}
        onAnsweredOnlyChange={onAnsweredOnlyChange}
        onPresetSelect={onPresetSelect}
        onClear={onClear}
      />
    );

    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Last 30 days" }));
    expect(onPresetSelect).toHaveBeenCalledWith(30);

    await user.click(screen.getByRole("checkbox", { name: /Only answered questions/i }));
    expect(onAnsweredOnlyChange).toHaveBeenCalledWith(false);

    await user.click(screen.getByRole("button", { name: "Clear all" }));
    expect(onClear).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Hide filters" }));
    expect(screen.getByText("6 filters active.")).toBeInTheDocument();
  });
});