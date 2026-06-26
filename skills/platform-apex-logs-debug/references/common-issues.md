# Common Debug Log Issues

## SOQL in loop

**Signals**
- repeating `SOQL_EXECUTE_BEGIN`
- query appears inside repeated method path

**Fix pattern**
- query once outside the loop
- use `Map<Id, SObject>` or grouped collections

## DML in loop

**Signals**
- repeated `DML_BEGIN`
- high DML statement count for small transactions

**Fix pattern**
- collect changes
- do one bulk DML operation

## Non-selective query

**Signals**
- high rows scanned
- slow query timing
- table-scan indicators

**Fix pattern**
- add indexed filters
- reduce scope
- use query-plan guidance

## CPU pressure

**Signals**
- CPU usage trending toward sync limit
- repeated expensive helper methods
- nested loops / repeated string work

**Fix pattern**
- reduce algorithmic complexity
- cache repeated work
- move heavy processing async where appropriate

## Heap pressure

**Signals**
- large collection allocations
- heap usage approaching sync limit

**Fix pattern**
- use SOQL for-loops
- reduce in-memory object size
- clear collections when done

## Null pointer / unhandled exceptions

**Signals**
- `EXCEPTION_THROWN`
- `FATAL_ERROR`
- clear stack trace with line numbers

**Fix pattern**
- guard null values
- make assumptions explicit
- improve result handling for empty query results
