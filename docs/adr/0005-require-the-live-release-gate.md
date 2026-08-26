# Require the live release gate

Every tagged release runs the complete build and live release gate, including the browser matrix and mounted Paper smoke tests for both supported versions. The exact locally built image that passes the gate is tagged and pushed to GHCR, so published bytes retain direct verification evidence. Sanitized gate evidence is uploaded after every successful or failed run and retained for 30 days.
