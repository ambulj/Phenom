"""
Spike A: Local Model Benchmark
Measures:
1. First-token latency, tokens per second, and VRAM use over 5 runs (reporting median)
2. Tool-call reliability across 20 sample prompts (checking valid JSON and expected tool)
3. 3,000-word document summary (timing and output quality)
"""

import json
import time
import subprocess
import statistics
import urllib.request
import urllib.error

OLLAMA_API_BASE = "http://localhost:11434"

def get_vram_usage_mb() -> float:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        )
        return float(out.strip().split("\n")[0])
    except Exception as e:
        return -1.0

def generate_stream(model: str, prompt: str, system: str = ""):
    url = f"{OLLAMA_API_BASE}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": True,
        "options": {
            "temperature": 0.2
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    start_time = time.perf_counter()
    first_token_time = None
    tokens = []
    
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            if not line:
                continue
            chunk = json.loads(line.decode("utf-8"))
            if first_token_time is None and chunk.get("response"):
                first_token_time = time.perf_counter()
            tokens.append(chunk.get("response", ""))
            if chunk.get("done"):
                total_duration_ns = chunk.get("total_duration", 0)
                eval_count = chunk.get("eval_count", len(tokens))
                eval_duration_ns = chunk.get("eval_duration", 0)
                break
                
    end_time = time.perf_counter()
    first_token_latency_ms = ((first_token_time or end_time) - start_time) * 1000.0
    
    if eval_duration_ns > 0:
        tps = eval_count / (eval_duration_ns / 1e9)
    else:
        elapsed = end_time - (first_token_time or start_time)
        tps = len(tokens) / elapsed if elapsed > 0 else 0.0
        
    return {
        "text": "".join(tokens),
        "first_token_ms": first_token_latency_ms,
        "tokens_per_second": tps,
        "eval_count": eval_count,
        "total_elapsed_s": end_time - start_time
    }

def benchmark_latency_and_throughput(model: str, runs: int = 5):
    print(f"\n--- Benchmarking Latency & Throughput for '{model}' ({runs} runs) ---")
    prompt = "Explain in three paragraphs how an operating system kernel manages virtual memory paging and hardware interrupts."
    
    # Warmup
    print("Running warmup...")
    generate_stream(model, "Hello, reply with one word.")
    
    first_token_latencies = []
    tps_list = []
    vram_usages = []
    
    for i in range(1, runs + 1):
        vram_before = get_vram_usage_mb()
        res = generate_stream(model, prompt)
        vram_after = get_vram_usage_mb()
        peak_vram = max(vram_before, vram_after)
        
        first_token_latencies.append(res["first_token_ms"])
        tps_list.append(res["tokens_per_second"])
        vram_usages.append(peak_vram)
        
        print(f" Run {i}: first_token={res['first_token_ms']:.1f}ms, tps={res['tokens_per_second']:.1f}, peak_vram={peak_vram:.0f}MB, tokens={res['eval_count']}")
        time.sleep(1)
        
    median_ft = statistics.median(first_token_latencies)
    median_tps = statistics.median(tps_list)
    median_vram = statistics.median(vram_usages)
    
    print(f"Summary for {model}:")
    print(f" Median First-Token Latency: {median_ft:.2f} ms")
    print(f" Median Tokens Per Second:   {median_tps:.2f} tps")
    print(f" Median VRAM Usage:          {median_vram:.0f} MB")
    
    return {
        "median_first_token_ms": median_ft,
        "median_tps": median_tps,
        "median_vram_mb": median_vram
    }

TOOL_SYSTEM_PROMPT = """You are a tool execution planner. 
Available tools:
- list_files(path: str)
- read_file(path: str)
- create_file(path: str, content: str)
- move_file(src: str, dest: str)
- recycle_file(path: str)
- open_app(app_name: str)
- close_app(app_name: str)
- list_running_apps()
- organize_downloads()
- get_system_status()

You MUST reply ONLY with valid JSON in the format:
{"tool": "<tool_name>", "args": {<arguments>}}
Do not write any introductory or concluding text. Strictly JSON.
"""

SAMPLE_PROMPTS = [
    ("Show me the files inside C:/Users/Public", "list_files"),
    ("Read what is written inside C:/Notes/todo.txt", "read_file"),
    ("Create a new note at C:/Notes/meeting.txt with content 'Project kickoff at 10 AM'", "create_file"),
    ("Move C:/Downloads/report.pdf to C:/Documents/report.pdf", "move_file"),
    ("Send C:/Temp/scratch.txt to the recycle bin", "recycle_file"),
    ("Launch Spotify for me", "open_app"),
    ("Kill the Discord process", "close_app"),
    ("What applications are currently running on my computer?", "list_running_apps"),
    ("Sort and organize my downloads folder by type and date", "organize_downloads"),
    ("Check the CPU, GPU, and RAM status of the machine", "get_system_status"),
    ("What files are in C:/Projects/Phenom?", "list_files"),
    ("Open the file C:/Config/settings.json so I can see its contents", "read_file"),
    ("Save a new text file at C:/Work/summary.txt containing 'Completed spike A'", "create_file"),
    ("Relocate C:/Downloads/invoice.pdf into C:/Finance/2026/invoice.pdf", "move_file"),
    ("Delete the temporary file C:/Temp/log.old to the trash", "recycle_file"),
    ("Open Calculator", "open_app"),
    ("Shut down Chrome", "close_app"),
    ("List all running processes right now", "list_running_apps"),
    ("Clean up duplicate downloads and organize the folder", "organize_downloads"),
    ("How much memory and battery does the system have right now?", "get_system_status")
]

def benchmark_tool_calling(model: str):
    print(f"\n--- Benchmarking Tool Calling / JSON Reliability for '{model}' (20 prompts) ---")
    valid_json_count = 0
    correct_tool_count = 0
    results = []
    
    url = f"{OLLAMA_API_BASE}/api/generate"
    
    for idx, (user_prompt, expected_tool) in enumerate(SAMPLE_PROMPTS, 1):
        payload = {
            "model": model,
            "prompt": user_prompt,
            "system": TOOL_SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                output_text = resp_data.get("response", "").strip()
                
            # Parse JSON
            parsed = json.loads(output_text)
            valid_json_count += 1
            
            tool_called = parsed.get("tool")
            is_correct_tool = (tool_called == expected_tool)
            if is_correct_tool:
                correct_tool_count += 1
                
            status_str = f"OK (tool={tool_called})" if is_correct_tool else f"WRONG TOOL (got={tool_called}, expected={expected_tool})"
            print(f" [{idx:02d}/20] Prompt: '{user_prompt[:35]}...' -> {status_str}")
            results.append({"prompt": user_prompt, "expected": expected_tool, "output": parsed, "valid": True, "correct": is_correct_tool})
        except json.JSONDecodeError:
            print(f" [{idx:02d}/20] Prompt: '{user_prompt[:35]}...' -> INVALID JSON: {output_text[:50]}")
            results.append({"prompt": user_prompt, "expected": expected_tool, "output": output_text, "valid": False, "correct": False})
        except Exception as e:
            print(f" [{idx:02d}/20] Prompt: '{user_prompt[:35]}...' -> ERROR: {e}")
            results.append({"prompt": user_prompt, "expected": expected_tool, "error": str(e), "valid": False, "correct": False})
            
    print(f"\nTool Call Results for {model}:")
    print(f" Valid JSON:     {valid_json_count} / {len(SAMPLE_PROMPTS)} ({valid_json_count/len(SAMPLE_PROMPTS)*100:.1f}%)")
    print(f" Correct Tool:   {correct_tool_count} / {len(SAMPLE_PROMPTS)} ({correct_tool_count/len(SAMPLE_PROMPTS)*100:.1f}%)")
    
    return {
        "valid_json": valid_json_count,
        "correct_tool": correct_tool_count,
        "total": len(SAMPLE_PROMPTS)
    }

def benchmark_3000_word_summary(model: str):
    print(f"\n--- Benchmarking 3,000-Word Document Summary for '{model}' ---")
    
    # Generate ~3000 words document
    section = """Operating systems provide an abstraction layer between hardware components and user applications. The core architectural elements include processor management, memory management, device input/output subsystems, file system management, and security boundaries. Virtual memory systems employ page tables, translation lookaside buffers (TLB), and demand paging algorithms such as Least Recently Used (LRU) and clock algorithms to handle physical memory overcommitment. When a referenced virtual page is not present in physical RAM, a page fault exception is generated by the memory management unit (MMU), invoking the kernel page fault handler to read the required block from secondary backing storage into an allocated frame. Inter-process communication primitives such as message queues, pipes, shared memory segments, and Unix domain sockets allow isolated processes to exchange structured information across user-kernel boundaries. Furthermore, preemptive scheduling algorithms balance compute-bound throughput with interactive latency using multi-level feedback queues and dynamic priority boosting. Modern kernels also implement control groups and namespaces to isolate namespaces and resource allocations for containerized workloads. Security isolation is maintained using hardware privilege rings, supervisor mode execution protection, and encrypted memory paging. Network stack architectures implement zero-copy ring buffers and interrupt coalescing to process multi-gigabit workloads without CPU saturation.\n\n"""
    
    # Repeat to exceed 3000 words
    doc_words = section * 18
    actual_word_count = len(doc_words.split())
    print(f"Document prepared: {actual_word_count} words.")
    
    prompt = f"Summarize the following technical document in 5 key executive bullet points:\n\n{doc_words}"
    
    start_time = time.perf_counter()
    res = generate_stream(model, prompt)
    elapsed = time.perf_counter() - start_time
    
    print(f"Summary generated in {elapsed:.2f} seconds ({res['tokens_per_second']:.1f} tps, {res['eval_count']} tokens).")
    print("Summary output:")
    print("--------------------------------------------------")
    print(res["text"].strip())
    print("--------------------------------------------------")
    
    return {
        "word_count": actual_word_count,
        "elapsed_s": elapsed,
        "tps": res["tokens_per_second"],
        "tokens": res["eval_count"],
        "summary": res["text"]
    }

if __name__ == "__main__":
    import sys
    model_to_test = sys.argv[1] if len(sys.argv) > 1 else "llama3:latest"
    print(f"Starting Spike A Benchmark for: {model_to_test}")
    
    perf = benchmark_latency_and_throughput(model_to_test, runs=5)
    tools = benchmark_tool_calling(model_to_test)
    summary = benchmark_3000_word_summary(model_to_test)
    
    out_file = f"spikes/a-local-model/results_{model_to_test.replace(':', '_')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"performance": perf, "tools": tools, "summary": {"elapsed_s": summary["elapsed_s"], "tps": summary["tps"], "tokens": summary["tokens"]}}, f, indent=2)
    print(f"\nResults saved to {out_file}")
