#!/usr/bin/env python3
"""
AI Council Discussion Script - Enhanced Version
Simulates a confrontational debate between 3 AI experts with voting, user feedback, and synthesis.
"""

import os
import sys
import random
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm

from groq import Groq
from google import genai
from openai import OpenAI


console = Console()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SAMBANOVA_API_KEY = os.environ.get("SAMBANOVA_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
sambanova_client = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url="https://api.sambanova.ai/v1"
) if SAMBANOVA_API_KEY else None

DEFAULT_PERSONALITIES = {
    "groq": {
        "name": "Dr. Logic",
        "color": "cyan",
        "style": "bold cyan",
        "personality": "You are Dr. Logic, an analytical AI expert who focuses on logical reasoning, data-driven insights, and systematic analysis. You are assertive and direct in debates.",
        "model": "llama-3.1-8b-instant"
    },
    "gemini": {
        "name": "Prof. Vision",
        "color": "green",
        "style": "bold green",
        "personality": "You are Prof. Vision, a creative AI expert who focuses on innovative ideas, future possibilities, and big-picture thinking. You are passionate and bold in defending your ideas.",
        "model": "gemini-2.5-flash"
    },
    "sambanova": {
        "name": "Dr. Practical",
        "color": "magenta",
        "style": "bold magenta",
        "personality": "You are Dr. Practical, a pragmatic AI expert who focuses on real-world applications, implementation challenges, and practical solutions. You are no-nonsense and results-oriented.",
        "model": "Meta-Llama-3.1-8B-Instruct"
    }
}

EXPERTS = {}
transcript = []
approved_ideas = []
user_feedback = ""


def log_transcript(entry_type: str, content: str, metadata: dict = None):
    """Log an entry to the transcript."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": entry_type,
        "content": content,
        "metadata": metadata or {}
    }
    transcript.append(entry)


def check_api_keys():
    """Check if all required API keys are set."""
    missing_keys = []
    if not GROQ_API_KEY:
        missing_keys.append("GROQ_API_KEY")
    if not GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY")
    if not SAMBANOVA_API_KEY:
        missing_keys.append("SAMBANOVA_API_KEY")
    
    if missing_keys:
        console.print(Panel(
            f"[red]Missing API keys: {', '.join(missing_keys)}[/red]\n\n"
            "Please set these environment variables to run the AI Council.",
            title="Configuration Error",
            border_style="red"
        ))
        return False
    return True


def get_ai_response(expert_key: str, prompt: str, system_prompt: str) -> str:
    """Get response from the appropriate AI based on expert key."""
    expert = EXPERTS[expert_key]
    
    try:
        if expert_key == "groq":
            if not groq_client:
                return "[Error: Groq client not initialized]"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            response = groq_client.chat.completions.create(
                model=expert["model"],
                messages=messages,
                max_tokens=600,
                temperature=0.8
            )
            return response.choices[0].message.content or "[No response]"
            
        elif expert_key == "gemini":
            if not gemini_client:
                return "[Error: Gemini client not initialized]"
            full_prompt = f"{system_prompt}\n\n{prompt}"
            response = gemini_client.models.generate_content(
                model=expert["model"],
                contents=full_prompt
            )
            return response.text or "[No response]"
            
        else:
            if not sambanova_client:
                return "[Error: SambaNova client not initialized]"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            response = sambanova_client.chat.completions.create(
                model=expert["model"],
                messages=messages,
                max_tokens=600,
                temperature=0.8
            )
            return response.choices[0].message.content or "[No response]"
            
    except Exception as e:
        return f"[Error: {str(e)}]"


def get_vote(expert_key: str, ideas_to_vote: list, topic: str) -> dict:
    """Get voting decisions from an AI expert."""
    expert = EXPERTS[expert_key]
    
    ideas_text = "\n".join([f"{i+1}. [{idea['expert']}]: {idea['key_idea']}" 
                           for i, idea in enumerate(ideas_to_vote)])
    
    prompt = f"""Topic: {topic}

The following key ideas have been proposed. For EACH idea, vote APPROVE or REJECT.
Be critical - only approve ideas that are genuinely strong and well-argued.

Ideas to vote on:
{ideas_text}

Respond in this exact JSON format:
{{"votes": [{{"idea_num": 1, "vote": "APPROVE or REJECT", "reason": "brief reason"}}]}}

Vote on ALL ideas listed above."""

    system_prompt = f"{expert['personality']}\n\nYou must respond with valid JSON only, no other text."
    
    response = get_ai_response(expert_key, prompt, system_prompt)
    
    try:
        clean_response = response.strip()
        if clean_response.startswith("```"):
            clean_response = clean_response.split("```")[1]
            if clean_response.startswith("json"):
                clean_response = clean_response[4:]
        votes = json.loads(clean_response)
        return votes
    except:
        return {"votes": [{"idea_num": i+1, "vote": "APPROVE", "reason": "Parse error - default approve"} 
                         for i in range(len(ideas_to_vote))]}


def extract_key_idea(expert_key: str, response: str, topic: str) -> str:
    """Extract the key idea from an expert's response."""
    prompt = f"""From the following argument about "{topic}", extract the ONE main key idea or proposal in a single concise sentence (max 30 words):

{response}

Respond with just the key idea, nothing else."""

    system_prompt = "Extract and summarize the main point concisely."
    
    result = get_ai_response(expert_key, prompt, system_prompt)
    return result.strip()[:200]


def display_response(expert_key: str, response: str):
    """Display an expert's response in the terminal."""
    expert = EXPERTS[expert_key]
    console.print()
    console.print(Panel(
        Markdown(response),
        title=f"[{expert['style']}]{expert['name']} ({expert_key.upper()})[/{expert['style']}]",
        border_style=expert["color"],
        padding=(1, 2)
    ))


def display_voting_results(ideas: list, all_votes: dict):
    """Display voting results in a table."""
    table = Table(title="Voting Results", show_header=True, header_style="bold")
    table.add_column("Expert", style="cyan")
    table.add_column("Key Idea", style="white", max_width=40)
    table.add_column("Approvals", style="green", justify="center")
    table.add_column("Rejections", style="red", justify="center")
    table.add_column("Status", justify="center")
    
    for i, idea in enumerate(ideas):
        approvals = 0
        rejections = 0
        
        for voter, votes in all_votes.items():
            if voter != idea["expert"]:
                for v in votes.get("votes", []):
                    if v.get("idea_num") == i + 1:
                        if v.get("vote", "").upper() == "APPROVE":
                            approvals += 1
                        else:
                            rejections += 1
        
        status = "[green]KEPT[/green]" if approvals > rejections else "[red]DELETED[/red]"
        idea["kept"] = approvals > rejections
        idea["approvals"] = approvals
        idea["rejections"] = rejections
        
        table.add_row(
            EXPERTS[idea["expert"]]["name"],
            idea["key_idea"][:40] + "..." if len(idea["key_idea"]) > 40 else idea["key_idea"],
            str(approvals),
            str(rejections),
            status
        )
    
    console.print()
    console.print(table)
    return [idea for idea in ideas if idea.get("kept", False)]


def run_round_1(topic: str, expert_order: list) -> list:
    """Run Round 1 - Independent perspectives without seeing others."""
    console.print()
    console.print(Panel(
        "[bold]ROUND 1: Independent Perspectives[/bold]\n"
        "Each expert presents their initial view without seeing others' arguments.",
        title="Round 1",
        border_style="yellow"
    ))
    log_transcript("round_start", "Round 1: Independent Perspectives")
    
    responses = []
    
    for expert_key in expert_order:
        expert = EXPERTS[expert_key]
        
        prompt = f"""Topic for discussion: {topic}

Present your independent perspective on this topic. This is Round 1, so you haven't heard from other experts yet.
Keep your response focused and concise (2-3 paragraphs). State your main argument clearly."""

        console.print()
        with console.status(f"[{expert['color']}]{expert['name']} is formulating their position...[/{expert['color']}]"):
            response = get_ai_response(expert_key, prompt, expert["personality"])
        
        display_response(expert_key, response)
        log_transcript("response", response, {"expert": expert_key, "round": 1})
        
        responses.append({
            "expert": expert_key,
            "round": 1,
            "response": response,
            "key_idea": ""
        })
    
    console.print()
    with console.status("[yellow]Extracting key ideas for voting...[/yellow]"):
        for resp in responses:
            resp["key_idea"] = extract_key_idea(resp["expert"], resp["response"], topic)
    
    return responses


def run_debate_round(topic: str, round_num: int, expert_order: list, 
                     previous_responses: list, kept_ideas: list) -> list:
    """Run a debate round where experts challenge each other."""
    global user_feedback
    
    console.print()
    console.print(Panel(
        f"[bold]ROUND {round_num}: Confrontational Debate[/bold]\n"
        "Experts must critique weaknesses in others' arguments and propose alternatives.",
        title=f"Round {round_num}",
        border_style="yellow"
    ))
    log_transcript("round_start", f"Round {round_num}: Confrontational Debate")
    
    context = "\n\n".join([
        f"[{EXPERTS[r['expert']]['name']}]: {r['response']}" 
        for r in previous_responses[-6:]
    ])
    
    kept_ideas_text = "\n".join([
        f"- {EXPERTS[idea['expert']]['name']}: {idea['key_idea']}" 
        for idea in kept_ideas
    ]) if kept_ideas else "No previously approved ideas yet."
    
    feedback_text = f"\n\nUSER GUIDANCE: {user_feedback}" if user_feedback else ""
    
    responses = []
    
    for expert_key in expert_order:
        expert = EXPERTS[expert_key]
        other_experts = [e for e in expert_order if e != expert_key]
        
        prompt = f"""Topic: {topic}

Previous discussion:
{context}

Currently approved ideas:
{kept_ideas_text}
{feedback_text}

You are in a DEBATE. You must:
1. CRITICIZE at least one specific weakness in another expert's argument (name them directly)
2. Propose a BETTER alternative or counter-argument
3. Only agree with an idea if it's genuinely superior to your position
4. Be assertive and direct - this is intellectual combat, not diplomacy

Challenge the arguments of: {', '.join([EXPERTS[e]['name'] for e in other_experts])}

Keep response concise but hard-hitting (2-3 paragraphs)."""

        console.print()
        with console.status(f"[{expert['color']}]{expert['name']} is preparing their challenge...[/{expert['color']}]"):
            response = get_ai_response(expert_key, prompt, expert["personality"])
        
        display_response(expert_key, response)
        log_transcript("response", response, {"expert": expert_key, "round": round_num})
        
        responses.append({
            "expert": expert_key,
            "round": round_num,
            "response": response,
            "key_idea": ""
        })
    
    console.print()
    with console.status("[yellow]Extracting key ideas for voting...[/yellow]"):
        for resp in responses:
            resp["key_idea"] = extract_key_idea(resp["expert"], resp["response"], topic)
    
    return responses


def run_voting(round_responses: list, topic: str) -> list:
    """Run the voting phase for a round's ideas."""
    console.print()
    console.print(Panel(
        "[bold]VOTING PHASE[/bold]\n"
        "Each expert votes APPROVE or REJECT on others' key ideas.",
        title="Voting",
        border_style="blue"
    ))
    
    all_votes = {}
    expert_keys = list(EXPERTS.keys())
    
    for expert_key in expert_keys:
        with console.status(f"[{EXPERTS[expert_key]['color']}]{EXPERTS[expert_key]['name']} is voting...[/{EXPERTS[expert_key]['color']}]"):
            votes = get_vote(expert_key, round_responses, topic)
            all_votes[expert_key] = votes
    
    kept_ideas = display_voting_results(round_responses, all_votes)
    
    log_transcript("voting", f"Voting completed. {len(kept_ideas)} ideas kept.", {
        "votes": all_votes,
        "kept_count": len(kept_ideas)
    })
    
    return kept_ideas


def get_user_feedback():
    """Get optional user feedback to guide the next round."""
    global user_feedback
    console.print()
    feedback = Prompt.ask(
        "[bold white]Enter guidance for the next round (or press Enter to skip)[/bold white]",
        default=""
    )
    if feedback.strip():
        user_feedback = feedback.strip()
        log_transcript("user_feedback", user_feedback)
        console.print(f"[dim]Guidance noted: {user_feedback}[/dim]")
    return feedback


def run_synthesis(topic: str, all_kept_ideas: list, all_responses: list):
    """Run the final synthesis round with a Summary Agent."""
    console.print()
    console.print(Panel(
        "[bold]FINAL SYNTHESIS[/bold]\n"
        "The Summary Agent reviews all approved ideas and creates a unified conclusion.",
        title="Synthesis Round",
        border_style="gold1"
    ))
    log_transcript("synthesis_start", "Final Synthesis Round")
    
    kept_ideas_text = "\n".join([
        f"- {EXPERTS[idea['expert']]['name']}: {idea['key_idea']} (Approvals: {idea.get('approvals', 0)})" 
        for idea in all_kept_ideas
    ])
    
    key_arguments = "\n\n".join([
        f"[{EXPERTS[r['expert']]['name']} - Round {r['round']}]: {r['response'][:500]}..."
        for r in all_responses[-9:]
    ])
    
    prompt = f"""Topic: {topic}

After a rigorous debate, the following ideas received majority approval:
{kept_ideas_text}

Key arguments from the discussion:
{key_arguments}

As the neutral Summary Agent, create a cohesive CONCLUSION paragraph that:
1. Combines the strongest approved arguments
2. Resolves any contradictions between them
3. Presents a unified, actionable synthesis
4. Acknowledges the key tensions that remain

Write a single, well-structured conclusion paragraph (4-6 sentences)."""

    system_prompt = "You are the Summary Agent - a neutral synthesizer who combines the best ideas from a debate into a coherent conclusion. Be balanced but decisive."
    
    with console.status("[gold1]Summary Agent is synthesizing the discussion...[/gold1]"):
        synthesis = get_ai_response("groq", prompt, system_prompt)
    
    console.print()
    console.print(Panel(
        Markdown(synthesis),
        title="[bold gold1]Summary Agent - Final Conclusion[/bold gold1]",
        border_style="gold1",
        padding=(1, 2)
    ))
    
    log_transcript("synthesis", synthesis)
    return synthesis


def save_transcript(topic: str, synthesis: str, num_rounds: int):
    """Save the complete transcript to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"council_transcript_{timestamp}.txt"
    
    with open(filename, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("AI COUNCIL DISCUSSION TRANSCRIPT\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Topic: {topic}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Rounds: {num_rounds}\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("PARTICIPANTS:\n")
        f.write("-" * 70 + "\n")
        for key, expert in EXPERTS.items():
            f.write(f"  - {expert['name']} ({key.upper()})\n")
        f.write("\n")
        
        f.write("-" * 70 + "\n")
        f.write("DISCUSSION LOG:\n")
        f.write("-" * 70 + "\n\n")
        
        for entry in transcript:
            f.write(f"[{entry['timestamp']}] {entry['type'].upper()}\n")
            if entry['metadata']:
                if 'expert' in entry['metadata']:
                    f.write(f"  Expert: {entry['metadata']['expert']}\n")
                if 'round' in entry['metadata']:
                    f.write(f"  Round: {entry['metadata']['round']}\n")
            f.write(f"{entry['content']}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("FINAL CONCLUSION:\n")
        f.write("=" * 70 + "\n\n")
        f.write(synthesis + "\n")
    
    console.print(f"\n[dim]Transcript saved to: {filename}[/dim]")
    return filename


def setup_personalities():
    """Allow user to customize AI personalities or use defaults."""
    global EXPERTS
    
    console.print()
    customize = Confirm.ask(
        "[bold white]Would you like to customize the AI personalities?[/bold white]",
        default=False
    )
    
    if customize:
        for key in ["groq", "gemini", "sambanova"]:
            default = DEFAULT_PERSONALITIES[key]
            console.print(f"\n[{default['color']}]Configuring {default['name']}:[/{default['color']}]")
            
            name = Prompt.ask("  Name", default=default["name"])
            personality = Prompt.ask(
                "  Personality/debating style",
                default=default["personality"]
            )
            
            EXPERTS[key] = {
                **default,
                "name": name,
                "personality": personality
            }
    else:
        EXPERTS = dict(DEFAULT_PERSONALITIES)
    
    log_transcript("setup", "Personalities configured", {
        "customized": customize,
        "experts": {k: {"name": v["name"]} for k, v in EXPERTS.items()}
    })


def main():
    """Main function to run the AI Council discussion."""
    global approved_ideas
    
    console.print(Panel(
        "[bold]Welcome to the AI Council - Enhanced Debate Mode[/bold]\n\n"
        "Features:\n"
        "  - Randomized speaking order each round\n"
        "  - Round 1: Independent perspectives\n"
        "  - Round 2+: Confrontational debate with criticism\n"
        "  - Voting system with idea approval/rejection\n"
        "  - User feedback between rounds\n"
        "  - Final synthesis by Summary Agent\n"
        "  - Full transcript saved to file",
        title="AI Council Discussion",
        border_style="blue"
    ))
    
    if not check_api_keys():
        sys.exit(1)
    
    setup_personalities()
    
    console.print()
    topic = Prompt.ask("[bold white]Enter a topic for discussion[/bold white]")
    
    if not topic.strip():
        console.print("[red]No topic provided. Exiting.[/red]")
        sys.exit(1)
    
    log_transcript("topic", topic)
    
    num_rounds = IntPrompt.ask(
        "[bold white]Number of discussion rounds[/bold white]",
        default=3
    )
    num_rounds = max(2, min(num_rounds, 10))
    
    console.print()
    console.print(Panel(
        f"[bold]{topic}[/bold]\n\n"
        f"Rounds: {num_rounds} + Final Synthesis",
        title="Discussion Topic",
        border_style="blue"
    ))
    
    all_responses = []
    all_kept_ideas = []
    expert_keys = list(EXPERTS.keys())
    
    random.shuffle(expert_keys)
    console.print(f"\n[dim]Round 1 speaking order: {', '.join([EXPERTS[k]['name'] for k in expert_keys])}[/dim]")
    
    round_1_responses = run_round_1(topic, expert_keys)
    all_responses.extend(round_1_responses)
    
    kept_ideas = run_voting(round_1_responses, topic)
    all_kept_ideas.extend(kept_ideas)
    
    get_user_feedback()
    
    for round_num in range(2, num_rounds + 1):
        random.shuffle(expert_keys)
        console.print(f"\n[dim]Round {round_num} speaking order: {', '.join([EXPERTS[k]['name'] for k in expert_keys])}[/dim]")
        
        round_responses = run_debate_round(topic, round_num, expert_keys, all_responses, all_kept_ideas)
        all_responses.extend(round_responses)
        
        kept_ideas = run_voting(round_responses, topic)
        all_kept_ideas.extend(kept_ideas)
        
        if round_num < num_rounds:
            get_user_feedback()
    
    synthesis = run_synthesis(topic, all_kept_ideas, all_responses)
    
    filename = save_transcript(topic, synthesis, num_rounds)
    
    console.print()
    console.print(Panel(
        f"[bold green]The AI Council debate has concluded![/bold green]\n\n"
        f"Topic: {topic}\n"
        f"Rounds completed: {num_rounds}\n"
        f"Ideas approved: {len(all_kept_ideas)}\n"
        f"Transcript: {filename}",
        title="Discussion Complete",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
