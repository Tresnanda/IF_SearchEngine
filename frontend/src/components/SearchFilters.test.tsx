import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SearchFilters from "./SearchFilters";

describe("SearchFilters", () => {
  it("renders options and triggers change handlers", () => {
    const onYearChange = vi.fn();
    const onDomainChange = vi.fn();

    render(
      <SearchFilters
        years={["2024", "2023"]}
        domains={["security", "sentiment"]}
        selectedYear="all"
        selectedDomain="all"
        onYearChange={onYearChange}
        onDomainChange={onDomainChange}
      />,
    );

    fireEvent.change(screen.getByLabelText("Year"), { target: { value: "2024" } });
    fireEvent.change(screen.getByLabelText("Domain"), { target: { value: "security" } });

    expect(onYearChange).toHaveBeenCalledWith("2024");
    expect(onDomainChange).toHaveBeenCalledWith("security");
  });

  it("disables year filter when year metadata is unavailable", () => {
    const onYearChange = vi.fn();
    const onDomainChange = vi.fn();

    render(
      <SearchFilters
        years={[]}
        domains={["security"]}
        selectedYear="all"
        selectedDomain="all"
        onYearChange={onYearChange}
        onDomainChange={onDomainChange}
      />,
    );

    const yearSelects = screen.getAllByLabelText("Year");
    expect(yearSelects[yearSelects.length - 1]).toBeDisabled();
    expect(screen.getByText("Year not available")).toBeInTheDocument();
  });
});
