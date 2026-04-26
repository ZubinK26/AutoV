
There are three resource managers named rm1, rm2, and rm3.
There is one transaction manager named tm.
Time proceeds in steps numbered 0 through 12.

At time 0, every resource manager is in the working state.
At time 0, the transaction manager is in the init state.
At time 0, no resource manager has crashed.
At time 0, the transaction manager has not crashed.

A resource manager is in exactly one state at each time step.
The possible states for a resource manager are working, prepared, committed, and aborted.
The transaction manager is in exactly one state at each time step.
The possible states for the transaction manager are init, collecting, committed, and aborted.

If a resource manager is in the working state at time T, then it may transition to the prepared state at time T plus 1.
If a resource manager is in the working state at time T, then it may transition to the aborted state at time T plus 1.
If a resource manager transitions to the prepared state at time T plus 1, then a prepared message from that resource manager is sent at time T plus 1.
If a resource manager transitions to the aborted state at time T plus 1 from the working state, then an abort message from that resource manager is sent at time T plus 1.

The transaction manager moves from the init state to the collecting state at time T plus 1 if it is in the init state at time T and has not crashed.
The transaction manager has received a prepared vote from a resource manager at time T if a prepared message from that resource manager was sent at any time before or equal to T.
The transaction manager has received an abort vote from a resource manager at time T if an abort message from that resource manager was sent at any time before or equal to T.

If the transaction manager is in the collecting state at time T, has received a prepared vote from rm1, rm2, and rm3 at time T, and has not crashed, then it transitions to the committed state at time T plus 1.
If the transaction manager is in the collecting state at time T, has received an abort vote from any resource manager at time T, and has not crashed, then it transitions to the aborted state at time T plus 1.

If the transaction manager transitions to the committed state at time T plus 1, then a commit message to every resource manager is sent at time T plus 1.
If the transaction manager transitions to the aborted state at time T plus 1, then an abort message to every resource manager is sent at time T plus 1.

A resource manager has received a commit message at time T if a commit message to that resource manager was sent at any time before or equal to T.
A resource manager has received an abort message at time T if an abort message to that resource manager was sent at any time before or equal to T.

If a resource manager is in the prepared state at time T, has received a commit message at time T, and has not crashed, then it transitions to the committed state at time T plus 1.
If a resource manager is in the prepared state at time T, has received an abort message at time T, and has not crashed, then it transitions to the aborted state at time T plus 1.

A resource manager that has crashed at time T remains crashed at all later times.
The transaction manager that has crashed at time T remains crashed at all later times.

A resource manager that has crashed does not change state.
The transaction manager that has crashed does not change state.

A resource manager or the transaction manager may crash at any time step.

The committed state is terminal: once a resource manager is in the committed state, it remains in the committed state.
The aborted state is terminal: once a resource manager is in the aborted state, it remains in the aborted state.