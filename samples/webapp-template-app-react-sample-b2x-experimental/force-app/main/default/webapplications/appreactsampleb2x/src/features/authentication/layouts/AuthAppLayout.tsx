import SessionTimeoutValidator from "../sessionTimeout/SessionTimeoutValidator";
import { AuthProvider } from "../context/AuthContext";
import AppLayout from "../../../appLayout";

export default function AuthAppLayout() {
	return (
		<AuthProvider>
			<SessionTimeoutValidator basePath="" />
			<AppLayout />
		</AuthProvider>
	);
}
