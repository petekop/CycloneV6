# Pester tests for launch_cyclone PowerShell script

Describe "launch_cyclone.ps1" {
    BeforeAll {
        # function to compute base directory based on environment variable
        function Get-BaseDir {
            param([string]$ScriptDir)
            if ($env:CYCLONE_BASE_DIR) {
                return $env:CYCLONE_BASE_DIR
            } else {
                return (Split-Path $ScriptDir -Parent)
            }
        }

        # function copied from scripts/launch_cyclone.ps1 for testing
        function Wait-ForServer {
            param(
                [string]$Url = "http://localhost:5050/api/health",
                [int]$TimeoutSeconds = 5
            )
            $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
            while ((Get-Date) -lt $deadline) {
                try {
                    $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 -Uri $Url
                    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                        return $true
                    }
                } catch {
                    # ignore failures and retry
                }
                Start-Sleep -Seconds 1
            }
            return $false
        }
    }

    Context "environment variable fallback" {
        It "uses CYCLONE_BASE_DIR when set" {
            $env:CYCLONE_BASE_DIR = "/custom/base"
            Get-BaseDir "/repo/scripts" | Should -Be "/custom/base"
            Remove-Item Env:CYCLONE_BASE_DIR
        }

        It "falls back to parent of script directory when env var not set" {
            Remove-Item Env:CYCLONE_BASE_DIR -ErrorAction SilentlyContinue
            Get-BaseDir "/repo/scripts" | Should -Be "/repo"
        }
    }

    Context "Wait-ForServer retry logic" {
        It "retries until Invoke-WebRequest succeeds" {
            $script:callCount = 0
            Mock Invoke-WebRequest {
                $script:callCount++
                if ($script:callCount -lt 3) {
                    throw "Failure"
                } else {
                    return @{ StatusCode = 200 }
                }
            }
            $result = Wait-ForServer -TimeoutSeconds 5
            $result | Should -BeTrue
            $script:callCount | Should -Be 3
        }

        It "returns false if all retries fail" {
            Mock Invoke-WebRequest { throw "Failure" }
            $result = Wait-ForServer -TimeoutSeconds 2
            $result | Should -BeFalse
        }
    }
}
