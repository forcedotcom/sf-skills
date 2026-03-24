/**
 * FiltersPanel Component
 *
 * Displays a panel of filter inputs for refining search results.
 * Supports both text inputs and select dropdowns based on filter affordance.
 *
 * @param filters - Array of filter definitions to display
 * @param picklistValues - Record of picklist values keyed by field path
 * @param loading - Whether filters are currently loading
 * @param onApplyFilters - Callback when filters are applied, receives filter values object
 *
 * @remarks
 * - Automatically initializes filter values from defaultValues
 * - Shows loading skeleton while filters are being fetched
 * - Supports "Apply Filters" and "Reset" actions
 * - Uses TanStack Form for form state management (similar to Login page)
 * - Uses FiltersForm wrapper for consistent UX/UI (similar to AuthForm pattern)
 *
 * @example
 * ```tsx
 * <FiltersPanel
 *   filters={filters}
 *   picklistValues={picklistValues}
 *   loading={false}
 *   onApplyFilters={(values) => applyFilters(values)}
 * />
 * ```
 */
import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../../../../components/ui/card";
import { Skeleton } from "../../../../components/ui/skeleton";
import { FiltersForm } from "../forms/filters-form";
import { Field, FieldLabel, FieldDescription } from "../../../../components/ui/field";
import { useAppForm, validateRangeValues } from "../../hooks/form";
import type { Filter, FilterCriteria } from "../../types/filters/filters";
import type { PicklistValue } from "../../types/filters/picklist";
import { parseFilterValue } from "../../utils/filterUtils";
import { sanitizeFilterValue } from "../../utils/sanitizationUtils";
import { getFormValueByPath } from "../../utils/formUtils";

interface FiltersPanelProps {
	filters: Filter[];
	picklistValues: Record<string, PicklistValue[]>;
	loading: boolean;
	objectApiName: string;
	onApplyFilters: (filterCriteria: FilterCriteria[]) => void;
}

export default function FiltersPanel({
	filters,
	picklistValues,
	loading,
	objectApiName,
	onApplyFilters,
}: FiltersPanelProps) {
	const [submitError, setSubmitError] = useState<string | null>(null);
	const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

	const defaultValues = useMemo(() => {
		if (!filters || !Array.isArray(filters)) {
			return {};
		}

		const values: Record<string, string> = {};
		filters.forEach((filter) => {
			if (filter && filter.targetFieldPath) {
				const affordance = filter.affordance?.toLowerCase() || "";

				if (affordance === "range") {
					const minFieldName = `${filter.targetFieldPath}_min`;
					const maxFieldName = `${filter.targetFieldPath}_max`;

					if (filter.defaultValues && filter.defaultValues.length >= 2) {
						values[minFieldName] = filter.defaultValues[0] || "";
						values[maxFieldName] = filter.defaultValues[1] || "";
					} else {
						values[minFieldName] = "";
						values[maxFieldName] = "";
					}
				} else {
					if (filter.defaultValues && filter.defaultValues.length > 0) {
						values[filter.targetFieldPath] = filter.defaultValues[0];
					} else {
						values[filter.targetFieldPath] = "";
					}
				}
			}
		});
		return values;
	}, [filters]);

	const form = useAppForm({
		defaultValues,
		onSubmit: async ({ value }) => {
			setSubmitError(null);
			setSubmitSuccess(null);
			try {
				const filterCriteria: FilterCriteria[] = [];

				for (const filter of filters) {
					if (!filter || !filter.targetFieldPath) {
						continue;
					}

					const affordance = filter.affordance?.toLowerCase() || "";

					if (affordance === "range") {
						const minFieldName = `${filter.targetFieldPath}_min`;
						const maxFieldName = `${filter.targetFieldPath}_max`;
						const minValueRaw = value[minFieldName] || "";
						const maxValueRaw = value[maxFieldName] || "";

						const minValue = sanitizeFilterValue(minValueRaw);
						const maxValue = sanitizeFilterValue(maxValueRaw);

						if (minValue && maxValue) {
							const rangeError = validateRangeValues(minValue, maxValue);
							if (rangeError) {
								setSubmitError(rangeError);
								return;
							}
						}

						if (minValue) {
							const parsedMin = parseFilterValue(minValue);
							if (parsedMin !== "") {
								filterCriteria.push({
									objectApiName,
									fieldPath: filter.targetFieldPath,
									operator: "gte",
									values: [parsedMin],
								});
							}
						}

						if (maxValue) {
							const parsedMax = parseFilterValue(maxValue);
							if (parsedMax !== "") {
								filterCriteria.push({
									objectApiName,
									fieldPath: filter.targetFieldPath,
									operator: "lte",
									values: [parsedMax],
								});
							}
						}
					} else {
						const fieldValueRaw =
							getFormValueByPath(value as Record<string, unknown>, filter.targetFieldPath) || "";
						const fieldValue = sanitizeFilterValue(fieldValueRaw);

						if (fieldValue) {
							if (affordance === "select") {
								filterCriteria.push({
									objectApiName,
									fieldPath: filter.targetFieldPath,
									operator: "eq",
									values: [fieldValue],
								});
							} else {
								const likeValue = `%${fieldValue}%`;
								filterCriteria.push({
									objectApiName,
									fieldPath: filter.targetFieldPath,
									operator: "like",
									values: [likeValue],
								});
							}
						}
					}
				}

				if (filterCriteria.length === 0) {
					setSubmitSuccess("No filters applied. Showing all results.");
				} else {
					setSubmitSuccess("Filters applied successfully");
				}

				onApplyFilters(filterCriteria);
			} catch (err) {
				const errorMessage = err instanceof Error ? err.message : "Failed to apply filters";
				setSubmitError(errorMessage);
			}
		},
		onSubmitInvalid: () => {},
	});

	const previousDefaultValuesRef = useRef<Record<string, string>>({});
	const previousLoadingRef = useRef<boolean>(true);

	useEffect(() => {
		const loadingJustCompleted = previousLoadingRef.current && !loading;
		const defaultValuesChanged =
			JSON.stringify(previousDefaultValuesRef.current) !== JSON.stringify(defaultValues);

		if (loadingJustCompleted && defaultValues && Object.keys(defaultValues).length > 0) {
			form.reset(defaultValues);
			previousDefaultValuesRef.current = defaultValues;
		} else if (defaultValuesChanged && !loading && Object.keys(defaultValues).length > 0) {
			form.reset(defaultValues);
			previousDefaultValuesRef.current = defaultValues;
		}

		previousLoadingRef.current = loading;
	}, [loading, defaultValues, form]);

	const handleSuccessDismiss = useCallback(() => {
		setSubmitSuccess(null);
	}, []);

	const handleReset = useCallback(() => {
		if (!filters || !Array.isArray(filters)) {
			form.reset();
			onApplyFilters([]);
			setSubmitError(null);
			setSubmitSuccess(null);
			return;
		}

		const resetValues: Record<string, string> = {};
		filters.forEach((filter) => {
			if (filter && filter.targetFieldPath) {
				const affordance = filter.affordance?.toLowerCase() || "";

				if (affordance === "range") {
					resetValues[`${filter.targetFieldPath}_min`] = "";
					resetValues[`${filter.targetFieldPath}_max`] = "";
				} else {
					resetValues[filter.targetFieldPath] = "";
				}
			}
		});
		form.reset(resetValues);
		onApplyFilters([]);
		setSubmitError(null);
		setSubmitSuccess(null);
	}, [filters, onApplyFilters, form]);

	if (loading) {
		return (
			<Card className="w-full" role="region" aria-label="Filters panel">
				<CardHeader>
					<CardTitle>Filters</CardTitle>
				</CardHeader>
				<CardContent
					className="space-y-4"
					role="status"
					aria-live="polite"
					aria-label="Loading filters"
				>
					<span className="sr-only">Loading filters</span>
					{[1, 2, 3].map((i) => (
						<div key={i} className="space-y-2" aria-hidden="true">
							<Skeleton className="h-4 w-24" />
							<Skeleton className="h-9 w-full" />
						</div>
					))}
				</CardContent>
			</Card>
		);
	}

	if (!filters || !Array.isArray(filters) || filters.length === 0) {
		return (
			<Card className="w-full" role="region" aria-label="Filters panel">
				<CardHeader>
					<CardTitle>Filters</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">No filters available</p>
				</CardContent>
			</Card>
		);
	}

	return (
		<form.AppForm>
			<FiltersForm
				title="Filters"
				description="Refine your search results by applying filters"
				error={submitError}
				success={submitSuccess}
				onSuccessDismiss={handleSuccessDismiss}
				submit={{
					text: "Apply Filters",
					loadingText: "Applying filters…",
				}}
				reset={{
					text: "Reset",
					onReset: handleReset,
				}}
			>
				{filters.map((filter) => {
					if (!filter || !filter.targetFieldPath) {
						return null;
					}

					const fieldPicklistValues = picklistValues[filter.targetFieldPath] || [];
					const affordance = filter.affordance?.toLowerCase() || "";

					if (affordance === "range") {
						const minFieldName = `${filter.targetFieldPath}_min`;
						const maxFieldName = `${filter.targetFieldPath}_max`;
						const inputType = "text";
						const placeholder =
							filter.attributes?.placeholder === "null"
								? undefined
								: filter.attributes?.placeholder;

						return (
							<Field key={filter.targetFieldPath}>
								<FieldLabel>{filter.label || filter.targetFieldPath}</FieldLabel>
								{filter.helpMessage && <FieldDescription>{filter.helpMessage}</FieldDescription>}
								<div
									className="grid grid-cols-2 gap-3"
									role="group"
									aria-label={`${filter.label || filter.targetFieldPath} range filter`}
								>
									<form.AppField name={minFieldName}>
										{(field) => (
											<field.FilterRangeMinField
												placeholder={placeholder || "Min"}
												type={inputType}
												aria-label={`${filter.label || filter.targetFieldPath} - Minimum`}
											/>
										)}
									</form.AppField>
									<form.AppField name={maxFieldName}>
										{(field) => (
											<field.FilterRangeMaxField
												placeholder={placeholder || "Max"}
												type={inputType}
												aria-label={`${filter.label || filter.targetFieldPath} - Maximum`}
											/>
										)}
									</form.AppField>
								</div>
							</Field>
						);
					}

					if (affordance === "select") {
						return (
							<form.AppField key={filter.targetFieldPath} name={filter.targetFieldPath}>
								{(field) => (
									<field.FilterSelectField
										label={filter.label || filter.targetFieldPath}
										description={filter.helpMessage || undefined}
										placeholder={filter.attributes?.placeholder || "Select..."}
										options={fieldPicklistValues}
									/>
								)}
							</form.AppField>
						);
					}

					return (
						<form.AppField key={filter.targetFieldPath} name={filter.targetFieldPath}>
							{(field) => (
								<field.FilterTextField
									label={filter.label || filter.targetFieldPath}
									description={filter.helpMessage || undefined}
									placeholder={
										filter.attributes?.placeholder ||
										`Enter ${(filter.label || filter.targetFieldPath).toLowerCase()}`
									}
								/>
							)}
						</form.AppField>
					);
				})}
			</FiltersForm>
		</form.AppForm>
	);
}
