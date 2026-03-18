import React from "react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import type { Application } from "../lib/types";

interface ApplicationCardProps {
	application: Application;
	onApprove: (id: string) => void;
	onReject: (id: string) => void;
}

export const ApplicationCard: React.FC<ApplicationCardProps> = ({
	application,
	onApprove,
	onReject,
}) => {
	return (
		<Card className="p-4 mb-3">
			<div className="flex items-start justify-between gap-4">
				<div className="flex items-start gap-3 flex-1">
					<span className="text-yellow-500 text-xl">🟡</span>
					<div className="flex-1 min-w-0">
						<h4 className="font-semibold text-gray-900 truncate">
							{application.applicantName} - {application.propertyAddress}
						</h4>
						<p className="text-sm text-gray-600 mt-1">Submitted: {application.submittedDate}</p>
					</div>
				</div>
				<div className="flex gap-2 flex-shrink-0">
					<Button
						onClick={() => onApprove(application.id)}
						className="bg-green-600 hover:bg-green-700"
					>
						Approve
					</Button>
					<Button onClick={() => onReject(application.id)} variant="destructive">
						Reject
					</Button>
				</div>
			</div>
		</Card>
	);
};
