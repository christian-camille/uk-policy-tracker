import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MembersPage from "./page";

const mockUseTrackedMembers = vi.fn();
const mockUseRefreshAllMembers = vi.fn();
const mockUseRefreshMember = vi.fn();
const mockUseTrackMember = vi.fn();
const mockUseUntrackMember = vi.fn();
const mockSearchMembers = vi.fn();

vi.mock("@/hooks/useMembers", () => ({
  useTrackedMembers: () => mockUseTrackedMembers(),
  useRefreshAllMembers: () => mockUseRefreshAllMembers(),
  useRefreshMember: () => mockUseRefreshMember(),
  useTrackMember: () => mockUseTrackMember(),
  useUntrackMember: () => mockUseUntrackMember(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    searchMembers: (...args: unknown[]) => mockSearchMembers(...args),
  },
}));

describe("MembersPage", () => {
  beforeEach(() => {
    mockUseTrackedMembers.mockReturnValue({
      data: { members: [] },
      isLoading: false,
      error: null,
    });
    mockUseRefreshAllMembers.mockReturnValue({
      isPending: false,
      isError: false,
      isSuccess: false,
      data: { members: 0 },
      mutate: vi.fn(),
    });
    mockUseRefreshMember.mockReturnValue({
      isPending: false,
      mutate: vi.fn(),
    });
    mockUseTrackMember.mockReturnValue({
      isPending: false,
      mutate: vi.fn(),
    });
    mockUseUntrackMember.mockReturnValue({
      isPending: false,
      mutate: vi.fn(),
    });
    mockSearchMembers.mockResolvedValue({ results: [], total: 0 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("opens the search panel from the empty state", async () => {
    render(<MembersPage />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Find an MP" }));

    expect(screen.getByLabelText("Search for an MP, Lord, or constituency")).toBeInTheDocument();
  });

  it("debounces member search, groups results, and tracks untracked members", async () => {
    vi.useFakeTimers();
    const trackMutate = vi.fn();
    mockUseTrackMember.mockReturnValue({
      isPending: false,
      mutate: trackMutate,
    });
    mockSearchMembers.mockResolvedValue({
      results: [
        {
          parliament_id: 1,
          name_display: "Rachel Reeves",
          party: "Labour",
          house: "Commons",
          constituency: "Leeds West",
          thumbnail_url: null,
          is_active: true,
          is_tracked: false,
          match_types: ["location"],
        },
        {
          parliament_id: 2,
          name_display: "Keir Starmer",
          party: "Labour",
          house: "Commons",
          constituency: "Holborn and St Pancras",
          thumbnail_url: null,
          is_active: true,
          is_tracked: false,
          match_types: ["name"],
        },
      ],
      total: 2,
    });

    render(<MembersPage />);

    fireEvent.click(screen.getByRole("button", { name: "Add Member" }));
    fireEvent.change(screen.getByLabelText("Search for an MP, Lord, or constituency"), {
      target: { value: "Keir" },
    });

    expect(mockSearchMembers).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(349);
    });
    expect(mockSearchMembers).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(1);
      await Promise.resolve();
    });
    vi.useRealTimers();

    await waitFor(() => {
      expect(mockSearchMembers).toHaveBeenCalledWith("Keir");
    });

    expect(await screen.findByText("Constituency Matches")).toBeInTheDocument();
    expect(screen.getByText("Name And Title Matches")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Track" })[0]);
    expect(trackMutate).toHaveBeenCalledWith(1);
  });

  it("renders refresh success feedback for tracked members", () => {
    mockUseRefreshAllMembers.mockReturnValue({
      isPending: false,
      isError: false,
      isSuccess: true,
      data: { members: 2 },
      mutate: vi.fn(),
    });

    render(<MembersPage />);

    expect(screen.getByText("Refresh completed for 2 members.")).toBeInTheDocument();
  });
});