'use client';

import * as React from 'react';
import { format } from 'date-fns';
import { Calendar as CalendarIcon } from 'lucide-react';

import type { DateRange, DayPickerProps } from 'react-day-picker';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';

function DatePicker({ ...props }: React.ComponentProps<typeof Popover>) {
  return <Popover data-slot="date-picker" {...props} />;
}

function DatePickerTrigger({
  className,
  children,
  date,
  placeholder = 'Pick a date',
  dateFormat = 'PPP',
  ...props
}: React.ComponentProps<typeof Button> & {
  date?: Date;
  placeholder?: string;
  dateFormat?: string;
}) {
  return (
    <PopoverTrigger asChild>
      <Button
        variant="outline"
        data-slot="date-picker-trigger"
        data-empty={!date}
        className={cn(
          'w-[280px] justify-start text-left font-normal data-[empty=true]:text-muted-foreground',
          className
        )}
        {...props}
      >
        {children ?? (
          <>
            <CalendarIcon />
            {date ? format(date, dateFormat) : <span>{placeholder}</span>}
          </>
        )}
      </Button>
    </PopoverTrigger>
  );
}

function DatePickerContent({
  className,
  ...props
}: React.ComponentProps<typeof PopoverContent>) {
  return (
    <PopoverContent
      data-slot="date-picker-content"
      className={cn('w-auto p-0', className)}
      {...props}
    />
  );
}

function DatePickerRangeTrigger({
  className,
  children,
  dateRange,
  placeholder = 'Pick a date',
  dateFormat = 'LLL dd, y',
  ...props
}: React.ComponentProps<typeof Button> & {
  dateRange?: DateRange;
  placeholder?: string;
  dateFormat?: string;
}) {
  const hasDate = dateRange?.from != null;
  return (
    <PopoverTrigger asChild>
      <Button
        variant="outline"
        data-slot="date-picker-range-trigger"
        data-empty={!hasDate}
        className={cn(
          'justify-start text-left font-normal data-[empty=true]:text-muted-foreground',
          className
        )}
        {...props}
      >
        {children ?? (
          <>
            <CalendarIcon />
            {dateRange?.from ? (
              dateRange.to ? (
                <>
                  {format(dateRange.from, dateFormat)} –{' '}
                  {format(dateRange.to, dateFormat)}
                </>
              ) : (
                format(dateRange.from, dateFormat)
              )
            ) : (
              <span>{placeholder}</span>
            )}
          </>
        )}
      </Button>
    </PopoverTrigger>
  );
}

function DatePickerCalendar(props: DayPickerProps) {
  return <Calendar data-slot="date-picker-calendar" {...props} />;
}

export {
  DatePicker,
  DatePickerTrigger,
  DatePickerRangeTrigger,
  DatePickerContent,
  DatePickerCalendar,
};
