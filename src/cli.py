# -*- coding: utf-8 -*-
"""
PurifyAI CLI - 命令行接口

提供 AOP 集成的命令行工具
"""

import argparse
import sys
from pathlib import Path


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="purifyai",
        description="PurifyAI - AI-powered disk cleanup tool with AOP integration"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # doctor 命令
    doctor_parser = subparsers.add_parser("doctor", help="Check environment and AOP status")
    doctor_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # aop 命令
    aop_parser = subparsers.add_parser("aop", help="AOP integration commands")
    aop_subparsers = aop_parser.add_subparsers(dest="aop_command")
    
    # aop review
    review_parser = aop_subparsers.add_parser("review", help="Run multi-agent code review")
    review_parser.add_argument("-p", "--prompt", required=True, help="Review prompt")
    review_parser.add_argument("-P", "--providers", help="Providers to use (comma-separated)")
    
    # aop hypothesis
    hypo_parser = aop_subparsers.add_parser("hypothesis", help="Manage hypotheses")
    hypo_subparsers = hypo_parser.add_subparsers(dest="hypo_command")
    
    hypo_create = hypo_subparsers.add_parser("create", help="Create a hypothesis")
    hypo_create.add_argument("statement", help="Hypothesis statement")
    hypo_create.add_argument("-p", "--priority", default="quick_win", help="Priority level")
    
    # aop learning
    learn_parser = aop_subparsers.add_parser("learning", help="Capture learnings")
    learn_parser.add_argument("--phase", default="build", help="Development phase")
    learn_parser.add_argument("--worked", help="What worked")
    learn_parser.add_argument("--failed", help="What failed")
    
    args = parser.parse_args()
    
    if args.command == "doctor":
        return cmd_doctor(args)
    elif args.command == "aop":
        return cmd_aop(args)
    else:
        parser.print_help()
        return 0


def cmd_doctor(args):
    """执行 doctor 命令"""
    import json
    from src.agent.aop_integration import get_aop
    
    aop = get_aop()
    
    if args.json:
        result = {
            "aop_available": aop.status.available,
            "aop_version": aop.status.version,
            "config_path": str(aop.status.config_path) if aop.status.config_path else None,
        }
        
        if aop.status.available:
            doctor_result = aop.doctor()
            result["providers"] = doctor_result.get("providers", [])
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("PurifyAI Environment Check")
        print("=" * 40)
        print(f"AOP Available: {'✅' if aop.status.available else '❌'}")
        
        if aop.status.available:
            print(f"AOP Version: {aop.status.version}")
            doctor_result = aop.doctor()
            print(f"\nProviders:")
            for p in doctor_result.get("providers", []):
                status = "✅" if p.get("available") else "❌"
                print(f"  {status} {p.get('provider')}")
        else:
            print("\nInstall AOP: pip install aop-agent")
        
        if aop.status.config_path:
            print(f"\nConfig: {aop.status.config_path}")
    
    return 0


def cmd_aop(args):
    """执行 AOP 命令"""
    from src.agent.aop_integration import get_aop
    
    aop = get_aop()
    
    if not aop.status.available:
        print("Error: AOP not installed. Run: pip install aop-agent")
        return 1
    
    if args.aop_command == "review":
        providers = args.providers.split(",") if args.providers else None
        result = aop.review(args.prompt, providers)
        
        if result["success"]:
            print(result["output"])
            print(f"\nFindings: {len(result['findings'])}")
        else:
            print(f"Error: {result['error']}")
            return 1
    
    elif args.aop_command == "hypothesis":
        if args.hypo_command == "create":
            result = aop.create_hypothesis(args.statement, args.priority)
            
            if result["success"]:
                print(f"✅ Hypothesis created: {result.get('hypothesis_id', 'N/A')}")
                if "file" in result:
                    print(f"   File: {result['file']}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
                return 1
    
    elif args.aop_command == "learning":
        result = aop.capture_learning(
            phase=args.phase,
            worked=args.worked,
            failed=args.failed
        )
        
        if result["success"]:
            print(f"✅ Learning captured")
            if "file" in result:
                print(f"   File: {result['file']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1
    
    else:
        print("Unknown AOP command")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())