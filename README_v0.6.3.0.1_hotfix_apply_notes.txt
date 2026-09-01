AthenaEngine v0.6.3.0.1 Hotfix Apply Notes

Extract this patch into:
F:\Development

Expected overlay target:
F:\Development\AthenaEngine

This patch fixes the two Studio failures caused by the root v0.6.3.0.0 change manifest being treated as unexpected root history.

After applying:
1. Restart Studio
2. Reload Build
3. Verify Build
4. Validate Everything

The root change manifest may still appear as release-hygiene cleanup residue until Safe Cleanup archives it. It should no longer fail Doctor/Validate Consensus Repository Cleanup.
