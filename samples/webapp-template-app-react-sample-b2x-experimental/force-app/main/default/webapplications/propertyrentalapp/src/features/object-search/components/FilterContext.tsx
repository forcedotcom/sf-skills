import { createContext, useContext, useCallback, type ReactNode } from "react";
import { Button } from "../../../components/ui/button";
import type { ActiveFilterValue } from "../utils/filterUtils";

interface FilterContextValue {
	filters: ActiveFilterValue[];
	onFilterChange: (field: string, value: ActiveFilterValue | undefined) => void;
	onFilterRemove: (field: string) => void;
	onReset: () => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

interface FilterProviderProps {
	filters: ActiveFilterValue[];
	onFilterChange: (field: string, value: ActiveFilterValue | undefined) => void;
	onFilterRemove: (field: string) => void;
	onReset: () => void;
	children: ReactNode;
}

export function FilterProvider({
	filters,
	onFilterChange,
	onFilterRemove,
	onReset,
	children,
}: FilterProviderProps) {
	return (
		<FilterContext.Provider
			value={{
				filters,
				onFilterChange,
				onFilterRemove,
				onReset,
			}}
		>
			{children}
		</FilterContext.Provider>
	);
}

function useFilterContext() {
	const ctx = useContext(FilterContext);
	if (!ctx) throw new Error("useFilterField must be used within a FilterProvider");
	return ctx;
}

export function useFilterField(field: string) {
	const { filters, onFilterChange, onFilterRemove } = useFilterContext();
	const value = filters.find((f) => f.field === field);
	const onChange = useCallback(
		(next: ActiveFilterValue | undefined) => {
			if (next) {
				onFilterChange(field, next);
			} else {
				onFilterRemove(field);
			}
		},
		[field, onFilterChange, onFilterRemove],
	);
	return { value, onChange };
}

export function useFilterPanel() {
	const { filters, onReset } = useFilterContext();
	return {
		hasActiveFilters: filters.length > 0,
		resetAll: onReset,
	};
}

type FilterResetButtonProps = Omit<React.ComponentProps<typeof Button>, "onClick">;

export function FilterResetButton({ children, ...props }: FilterResetButtonProps) {
	const { hasActiveFilters, resetAll } = useFilterPanel();
	if (!hasActiveFilters) return null;
	return (
		<Button onClick={resetAll} aria-label="Reset filters" variant="destructive" {...props}>
			{children ?? "Reset"}
		</Button>
	);
}
