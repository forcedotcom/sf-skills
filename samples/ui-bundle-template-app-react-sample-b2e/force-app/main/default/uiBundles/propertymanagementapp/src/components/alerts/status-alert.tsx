import { cva, type VariantProps } from 'class-variance-authority';
import { AlertCircleIcon, CheckCircle2Icon, InfoIcon } from 'lucide-react';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { useId } from 'react';

const statusAlertVariants = cva('', {
  variants: {
    variant: {
      error: '',
      success: '',
      info: 'text-blue-600 *:[svg]:text-current *:data-[slot=alert-description]:text-blue-600/90',
    },
  },
  defaultVariants: {
    variant: 'error',
  },
});

interface StatusAlertProps extends VariantProps<typeof statusAlertVariants> {
  children?: React.ReactNode;
  /** Alert variant type. @default "error" */
  variant?: 'error' | 'success' | 'info';
}

/**
 * Status alert component for displaying error, success, or info messages.
 * Returns null if no children are provided.
 */
export function StatusAlert({ children, variant = 'error' }: StatusAlertProps) {
  const descriptionId = useId();
  if (!children) return null;

  const isError = variant === 'error';

  const icon = {
    error: <AlertCircleIcon aria-hidden="true" />,
    success: <CheckCircle2Icon aria-hidden="true" />,
    info: <InfoIcon aria-hidden="true" />,
  }[variant];

  return (
    <Alert
      variant={isError ? 'destructive' : 'default'}
      className={statusAlertVariants({ variant })}
      aria-describedby={descriptionId}
      role={isError ? 'alert' : 'status'}
    >
      {icon}
      <AlertDescription id={descriptionId}>{children}</AlertDescription>
    </Alert>
  );
}
