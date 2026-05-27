import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WatchlistPage from "./page";

const mockUseTopics = vi.fn();
const mockUseCreateTopic = vi.fn();
const mockUseRefreshAllTopics = vi.fn();

vi.mock("@/components/TopicCard", () => ({
  TopicCard: ({ topic }: { topic: { label: string } }) => <div data-testid="topic-card">{topic.label}</div>,
}));

vi.mock("@/hooks/useTopics", () => ({
  useTopics: () => mockUseTopics(),
  useCreateTopic: () => mockUseCreateTopic(),
  useRefreshAllTopics: () => mockUseRefreshAllTopics(),
}));

describe("WatchlistPage", () => {
  beforeEach(() => {
    mockUseTopics.mockReturnValue({
      data: { topics: [] },
      isLoading: false,
      error: null,
    });
    mockUseCreateTopic.mockReturnValue({
      isPending: false,
      isError: false,
      mutate: vi.fn(),
    });
    mockUseRefreshAllTopics.mockReturnValue({
      isPending: false,
      isError: false,
      isSuccess: false,
      data: { topics: 0 },
      mutate: vi.fn(),
    });
  });

  it("does not submit a topic when the label is only whitespace", async () => {
    const mutate = vi.fn();
    mockUseCreateTopic.mockReturnValue({
      isPending: false,
      isError: false,
      mutate,
    });

    render(<WatchlistPage />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Add Topic" }));
    await user.type(screen.getByLabelText("Topic name"), "   ");
    await user.click(screen.getByRole("button", { name: "Create Topic" }));

    expect(mutate).not.toHaveBeenCalled();
  });

  it("submits parsed topic payloads and resets the form on success", async () => {
    const mutate = vi.fn((_payload, options?: { onSuccess?: () => void }) => {
      options?.onSuccess?.();
    });
    mockUseCreateTopic.mockReturnValue({
      isPending: false,
      isError: false,
      mutate,
    });

    render(<WatchlistPage />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Add Topic" }));
    await user.type(screen.getByLabelText("Topic name"), " Planning Reform ");
    await user.type(screen.getByLabelText(/Include any of these/i), "planning reform, local government");
    await user.click(screen.getByRole("button", { name: "Add required group" }));
    await user.type(screen.getByLabelText(/Require at least one of these \(2\)/i), "zoning, planning bill");
    await user.type(screen.getByLabelText(/Exclude any of these/i), "consultation, response");
    await user.click(screen.getByRole("button", { name: "Create Topic" }));

    expect(mutate).toHaveBeenCalledWith(
      {
        label: "Planning Reform",
        searchQueries: ["planning reform", "local government", "zoning", "planning bill"],
        keywordGroups: [
          ["planning reform", "local government"],
          ["zoning", "planning bill"],
        ],
        excludedKeywords: ["consultation", "response"],
      },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
    expect(screen.queryByLabelText("Topic name")).not.toBeInTheDocument();
  });

  it("renders refresh feedback banners from the mutation state", () => {
    mockUseRefreshAllTopics.mockReturnValue({
      isPending: false,
      isError: false,
      isSuccess: true,
      data: { topics: 2 },
      mutate: vi.fn(),
    });

    render(<WatchlistPage />);

    expect(screen.getByText("Refresh completed for 2 topics.")).toBeInTheDocument();
  });

  it("renders a refresh error banner when the mutation fails", () => {
    mockUseRefreshAllTopics.mockReturnValue({
      isPending: false,
      isError: true,
      isSuccess: false,
      data: { topics: 0 },
      mutate: vi.fn(),
    });

    render(<WatchlistPage />);

    expect(screen.getByText("Failed to refresh all topics. Try again after the upstream APIs recover.")).toBeInTheDocument();
  });
});