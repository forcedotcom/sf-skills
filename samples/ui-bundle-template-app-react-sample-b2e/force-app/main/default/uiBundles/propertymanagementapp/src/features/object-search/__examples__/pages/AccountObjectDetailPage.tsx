import { useState } from "react";
import { useParams, useNavigate } from "react-router";
import { createDataSDK } from "@salesforce/sdk-data";
import { AlertCircle, ChevronDown, ChevronRight, FileQuestion } from "lucide-react";
import GET_ACCOUNT_DETAIL from "../api/query/getAccountDetail.graphql?raw";
import type {
	GetAccountDetailQuery,
	GetAccountDetailQueryVariables,
} from "../../../../api/graphql-operations-types";
import { Alert, AlertTitle, AlertDescription } from "../../../../components/ui/alert";
import { Button } from "../../../../components/ui/button";
import { Card, CardContent } from "../../../../components/ui/card";
import { fieldValue, getAddressFieldLines, formatDateTimeField } from "../../utils/fieldUtils";
import {
	Collapsible,
	CollapsibleTrigger,
	CollapsibleContent,
} from "../../../../components/ui/collapsible";
import { Separator } from "../../../../components/ui/separator";
import { Skeleton } from "../../../../components/ui/skeleton";
import { useCachedAsyncData } from "../../hooks/useCachedAsyncData";
import { ObjectBreadcrumb } from "../../components/ObjectBreadcrumb";

type AccountNode = NonNullable<
	NonNullable<
		NonNullable<NonNullable<GetAccountDetailQuery["uiapi"]["query"]["Account"]>["edges"]>[number]
	>["node"]
>;

async function fetchAccountDetail(recordId: string): Promise<AccountNode | null | undefined> {
	const data = await createDataSDK();
	const response = await data.graphql?.<GetAccountDetailQuery, GetAccountDetailQueryVariables>(
		GET_ACCOUNT_DETAIL,
		{ id: recordId },
	);

	if (response?.errors?.length) {
		throw new Error(response.errors.map((e) => e.message).join("; "));
	}

	return response?.data?.uiapi?.query?.Account?.edges?.[0]?.node;
}

export default function AccountObjectDetail() {
	const { recordId } = useParams();
	const navigate = useNavigate();

	const {
		data: account,
		loading,
		error,
	} = useCachedAsyncData(() => fetchAccountDetail(recordId!), [recordId], {
		key: `account:${recordId}`,
	});

	return (
		<div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
			<ObjectBreadcrumb
				listPath="/accounts"
				listLabel="Accounts"
				loading={loading}
				recordName={
					account
						? (fieldValue(account.Name) ?? "")
						: error
							? "Error"
							: loading
								? undefined
								: "Not Found"
				}
			/>

			{/* Loading state */}
			{loading && <AccountDetailSkeleton />}

			{/* Error state */}
			{error && <AccountDetailError onBack={() => navigate(-1)} />}

			{/* Not found state */}
			{!loading && !error && !account && <AccountDetailNotFound onBack={() => navigate(-1)} />}

			{/* Content */}
			{account && <AccountDetailContent account={account} />}
		</div>
	);
}

function AccountDetailContent({ account }: { account: AccountNode }) {
	const billingAddress = getAddressFieldLines({
		street: fieldValue(account.BillingStreet),
		city: fieldValue(account.BillingCity),
		state: fieldValue(account.BillingState),
		postalCode: fieldValue(account.BillingPostalCode),
		country: fieldValue(account.BillingCountry),
	});

	const shippingAddress = getAddressFieldLines({
		street: fieldValue(account.ShippingStreet),
		city: fieldValue(account.ShippingCity),
		state: fieldValue(account.ShippingState),
		postalCode: fieldValue(account.ShippingPostalCode),
		country: fieldValue(account.ShippingCountry),
	});

	const dateTimeOptions = { dateStyle: "medium", timeStyle: "short" } as const;
	const createdDate = formatDateTimeField(
		fieldValue(account.CreatedDate),
		undefined,
		dateTimeOptions,
	);
	const lastModifiedDate = formatDateTimeField(
		fieldValue(account.LastModifiedDate),
		undefined,
		dateTimeOptions,
	);

	return (
		<>
			<h1 className="text-2xl font-bold mb-4">Account: {fieldValue(account.Name)}</h1>

			<Card>
				<CardContent className="space-y-8 pt-6">
					{/* Top section */}
					<div>
						<div className="space-y-4">
							<FieldRow>
								<FieldItem label="Account Owner">{fieldValue(account.Owner?.Name)}</FieldItem>
								<FieldItem label="Phone">
									<TelephoneField value={fieldValue(account.Phone)} />
								</FieldItem>
							</FieldRow>
							<FieldRow>
								<FieldItem label="Account Name">{fieldValue(account.Name)}</FieldItem>
								<FieldItem label="Fax">
									<TelephoneField value={fieldValue(account.Fax)} />
								</FieldItem>
							</FieldRow>
							<FieldRow>
								<FieldItem label="Parent Account">{fieldValue(account.Parent?.Name)}</FieldItem>
								<FieldItem label="Website">{fieldValue(account.Website)}</FieldItem>
							</FieldRow>
						</div>
					</div>

					<Separator />

					{/* Additional Information */}
					<Section title="Additional Information">
						<FieldRow>
							<FieldItem label="Type">{fieldValue(account.Type)}</FieldItem>
							<FieldItem label="Employees">{fieldValue(account.NumberOfEmployees)}</FieldItem>
						</FieldRow>
						<FieldRow>
							<FieldItem label="Industry">{fieldValue(account.Industry)}</FieldItem>
							<FieldItem label="Annual Revenue">{fieldValue(account.AnnualRevenue)}</FieldItem>
						</FieldRow>
						<FieldItem label="Description">{fieldValue(account.Description)}</FieldItem>
					</Section>

					<Separator />

					{/* Address Information */}
					<Section title="Address Information">
						<FieldRow>
							<FieldItem label="Billing Address">
								{billingAddress ? billingAddress.map((line, i) => <div key={i}>{line}</div>) : null}
							</FieldItem>
							<FieldItem label="Shipping Address">
								{shippingAddress
									? shippingAddress.map((line, i) => <div key={i}>{line}</div>)
									: null}
							</FieldItem>
						</FieldRow>
					</Section>

					<Separator />

					{/* System Information */}
					<Section title="System Information">
						<FieldRow>
							<FieldItem label="Created By">
								{[fieldValue(account.CreatedBy?.Name), createdDate].filter(Boolean).join(" ") ||
									null}
							</FieldItem>
							<FieldItem label="Last Modified By">
								{[fieldValue(account.LastModifiedBy?.Name), lastModifiedDate]
									.filter(Boolean)
									.join(" ") || null}
							</FieldItem>
						</FieldRow>
					</Section>
				</CardContent>
			</Card>
		</>
	);
}

function TelephoneField({ value }: { value?: string | null }) {
	if (!value) return null;
	return (
		<a href={`tel:${value}`} className="underline">
			{value}
		</a>
	);
}

function FieldItem({ label, children }: { label: string; children: React.ReactNode }) {
	return (
		<div>
			<dt className="text-sm text-muted-foreground">{label}</dt>
			<dd className="mt-0.5">{children ?? "—"}</dd>
		</div>
	);
}

function FieldRow({ children }: { children: React.ReactNode }) {
	return <div className="grid grid-cols-2 gap-x-8 gap-y-4">{children}</div>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
	const [open, setOpen] = useState(true);
	return (
		<Collapsible open={open} onOpenChange={setOpen}>
			<CollapsibleTrigger className="flex items-center gap-2 cursor-pointer text-lg font-semibold py-2">
				{open ? <ChevronDown className="size-5" /> : <ChevronRight className="size-5" />}
				{title}
			</CollapsibleTrigger>
			<CollapsibleContent>
				<div className="mt-2 space-y-4">{children}</div>
			</CollapsibleContent>
		</Collapsible>
	);
}

function AccountDetailError({ onBack }: { onBack: () => void }) {
	return (
		<>
			<Alert variant="destructive" role="alert">
				<AlertCircle />
				<AlertTitle>
					<h2>Failed to load account</h2>
				</AlertTitle>
				<AlertDescription>
					Something went wrong while loading this account. Please try again later.
				</AlertDescription>
			</Alert>
			<div className="mt-4 flex gap-3">
				<Button variant="outline" onClick={onBack}>
					← Back
				</Button>
				<Button variant="outline" onClick={() => window.location.reload()}>
					Retry
				</Button>
			</div>
		</>
	);
}

function AccountDetailNotFound({ onBack }: { onBack: () => void }) {
	return (
		<Card>
			<CardContent className="flex flex-col items-center justify-center py-16 text-center">
				<FileQuestion className="size-12 text-muted-foreground mb-4" />
				<h2 className="text-lg font-semibold mb-1">Account not found</h2>
				<p className="text-sm text-muted-foreground mb-6">
					The account you're looking for doesn't exist or may have been deleted.
				</p>
				<Button variant="outline" onClick={onBack}>
					← Go back
				</Button>
			</CardContent>
		</Card>
	);
}

function AccountDetailSkeleton() {
	return (
		<>
			<Skeleton className="h-8 w-56 mb-4" />

			<Card>
				<CardContent className="space-y-8 pt-6">
					{/* Top section: field rows */}
					<div>
						<div className="space-y-4">
							<SkeletonFieldRow />
							<SkeletonFieldRow />
							<SkeletonFieldRow />
						</div>
					</div>

					<Separator />

					{/* Additional Information */}
					<SkeletonSection />

					<Separator />

					{/* Address Information */}
					<div className="space-y-4">
						<Skeleton className="h-7 w-48 py-2" />
						<div className="grid grid-cols-2 gap-x-8 gap-y-4">
							<div>
								<Skeleton className="h-4 w-28 mb-1.5" />
								<Skeleton className="h-5 w-44 mb-1" />
								<Skeleton className="h-5 w-36 mb-1" />
								<Skeleton className="h-5 w-28" />
							</div>
							<div>
								<Skeleton className="h-4 w-32 mb-1.5" />
								<Skeleton className="h-5 w-44 mb-1" />
								<Skeleton className="h-5 w-36 mb-1" />
								<Skeleton className="h-5 w-28" />
							</div>
						</div>
					</div>

					<Separator />

					{/* System Information */}
					<div className="space-y-4">
						<Skeleton className="h-7 w-48 py-2" />
						<SkeletonFieldRow />
					</div>
				</CardContent>
			</Card>
		</>
	);
}

function SkeletonField() {
	return (
		<div>
			<Skeleton className="h-4 w-24 mb-1.5" />
			<Skeleton className="h-5 w-40" />
		</div>
	);
}

function SkeletonFieldRow() {
	return (
		<div className="grid grid-cols-2 gap-x-8 gap-y-4">
			<SkeletonField />
			<SkeletonField />
		</div>
	);
}

function SkeletonSection() {
	return (
		<div className="space-y-4">
			<Skeleton className="h-7 w-48 py-2" />
			<SkeletonFieldRow />
			<SkeletonFieldRow />
		</div>
	);
}
