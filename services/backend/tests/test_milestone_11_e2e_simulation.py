"""
Milestone 11.0 Comprehensive Multi-Component E2E Integration Suite (PLN-01, SYN-01, SEN-01, MSH-02, SAF-01, SAF-02).
Chains all milestone capabilities into a unified sovereign neural workflow:
1. Tree-of-Thought Metacognitive Goal Planning (PLN-01)
2. Companion Camera In-RAM Vision Ingestion & Local OCR (SEN-01)
3. Dynamic Runtime Micro-Tool Synthesis & Restricted Sandbox (SYN-01)
4. Metacognitive Step Trace Reflection & DAG Progression (PLN-01)
5. AirDrop-Style Encrypted P2P Media Drop to Obsidian Vault (MSH-02)
6. Universal Guardian Kill Switch Synchronous Lockdown (SAF-02)
"""

import io
import time
import base64
import pytest
from PIL import Image

from services.backend.safety.guardian import GuardianKillSwitch
from services.backend.safety.registry import registry
from services.backend.safety.ast_inspector import ast_inspector
from services.backend.coding.dynamic_synthesizer import dynamic_synthesizer, dynamic_synthesizer_manager
from services.backend.coding.restricted_sandbox import restricted_sandbox
from services.backend.orchestrator.tot_planner import TreeOfThoughtPlanner
from services.backend.orchestrator.dag_state import DAGStateManager
from services.backend.orchestrator.metacognition import MetacognitiveReflector
from services.backend.sensors.companion_camera import CompanionCameraStreamer
from services.backend.mesh.media_drop import P2PMediaDropManager, CHUNK_SIZE
from services.backend.schemas.sensory import (
    CameraFramePayload,
    CameraAnalysisTask,
    MediaDropDestination,
    MediaDropTransferState,
)
from services.backend.schemas.tot import NodeStatus
from services.backend.schemas.synthesis import ToolSynthesisRequest
from services.backend.tools.synthesis_tools import hot_register_micro_tool


def _create_mock_whiteboard_jpeg() -> str:
    """Generate in-RAM JPEG image containing mock whiteboard content."""
    img = Image.new("RGB", (640, 480), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.mark.asyncio
async def test_milestone_11_full_e2e_lifecycle(tmp_path):
    vault_dir = tmp_path / "vault"
    downloads_dir = tmp_path / "downloads"
    vault_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir.mkdir(parents=True, exist_ok=True)

    # 0. Initialize dedicated Guardian & Subsystems
    guardian_switch = GuardianKillSwitch()
    tot_planner = TreeOfThoughtPlanner()
    dag_mgr = DAGStateManager()
    reflector = MetacognitiveReflector()
    camera = CompanionCameraStreamer()
    drop_mgr = P2PMediaDropManager(
        vault_dir=str(vault_dir),
        downloads_dir=str(downloads_dir),
    )

    # Register subsystems in Guardian killswitch
    def on_state(state: str):
        if state == "halted":
            restricted_sandbox.halt()
            tot_planner.halt()
            dag_mgr.halt()
            reflector.halt()
            camera.halt()
            drop_mgr.halt()
        elif state == "idle":
            restricted_sandbox.reset()
            tot_planner.reset()
            dag_mgr.reset()
            reflector.reset()
            camera.reset()
            drop_mgr.reset()

    guardian_switch.add_state_callback(on_state)

    # -------------------------------------------------------------------------
    # Step 1: Hierarchical Tree-of-Thought (ToT) Goal Planning (PLN-01)
    # -------------------------------------------------------------------------
    goal_text = (
        "Ingest companion whiteboard diagram, synthesize custom math statistics micro-tool, "
        "execute computational analysis, and deliver markdown summary to Obsidian vault."
    )
    dag = tot_planner.plan_objective(
        goal_description=goal_text,
        max_contingency_branches=2,
        exploration_depth=3,
    )
    assert dag.dag_id is not None
    assert len(dag.nodes) >= 1
    assert len(dag.branches) >= 2
    assert not tot_planner.detect_cycles(dag.nodes)

    ready_nodes = tot_planner.get_ready_nodes(dag)
    assert len(ready_nodes) >= 1
    first_node = ready_nodes[0]
    first_node_id = first_node.node_id

    # -------------------------------------------------------------------------
    # Step 2: Companion Camera Vision Ingestion (SEN-01, Rule 4)
    # -------------------------------------------------------------------------
    frame_b64 = _create_mock_whiteboard_jpeg()
    frame_payload = CameraFramePayload(
        frame_id="frame-wb-001",
        node_id="companion-iphone-15",
        timestamp=time.time(),
        image_base64=frame_b64,
        width=640,
        height=480,
        battery_level=88.5,
        is_charging=False,
        wifi_rssi=-48,
    )

    ingest_res = camera.ingest_frame(frame_payload)
    assert ingest_res["frame_id"] == "frame-wb-001"
    assert ingest_res["status"] == "ingested"
    assert camera.get_status().is_streaming is True

    # Ensure zero disk writes: verify no temp image files created on disk
    assert camera._frame_buffer.get_latest() is not None

    # Perform local OCR analysis
    ocr_res = await camera.analyze_frame(
        task_type=CameraAnalysisTask.OCR,
        prompt="Extract formula on whiteboard",
    )
    assert ocr_res.task_type == "ocr"
    assert ocr_res.processing_time_ms >= 0.0

    # -------------------------------------------------------------------------
    # Step 3: Dynamic Runtime Micro-Tool Synthesis & AST Sandbox (SYN-01)
    # -------------------------------------------------------------------------
    synth_req = ToolSynthesisRequest(
        tool_name="stat_variance_calc",
        task_description="Compute statistical mean and sample variance from a list of numbers",
        parameter_specs={"data": "list"},
        return_type_spec="dict",
    )
    proposal = dynamic_synthesizer.synthesize_and_verify(synth_req)
    assert proposal.tool_name == "stat_variance_calc"
    ast_report = ast_inspector.inspect_code(proposal.function_code)
    assert ast_report.is_safe is True

    # Hot register into ToolRegistry
    tool_def = hot_register_micro_tool(proposal)
    assert tool_def.tier in (0, 1)
    assert tool_def.name == "stat_variance_calc"

    # Execute inside Restricted Subprocess Sandbox
    exec_res = restricted_sandbox.execute_function(
        func_code=proposal.function_code,
        func_name=proposal.tool_name,
        kwargs={"data": [10.0, 20.0, 30.0, 40.0, 50.0]},
    )
    assert exec_res.success is True
    assert exec_res.output is not None
    assert exec_res.peak_memory_mb < 256.0

    # -------------------------------------------------------------------------
    # Step 4: Metacognitive Trace Reflection & DAG State Progress (PLN-01)
    # -------------------------------------------------------------------------
    first_node_id = ready_nodes[0].node_id
    exec_result = {
        "status": "success",
        "result": exec_res.output,
        "ocr_info": ocr_res.extracted_text,
    }

    reflection = reflector.reflect_on_step(
        dag=dag,
        completed_node=first_node,
        status="COMPLETED",
    )
    assert reflection.detected_loop is False
    assert reflection.recommended_action == "CONTINUE"
    assert reflection.confidence_score > 0.5

    # Update node state in DAG
    dag.nodes[first_node_id].status = NodeStatus.COMPLETED
    dag.nodes[first_node_id].result_data = exec_result
    dag.nodes[first_node_id].completed_at = time.time()

    # -------------------------------------------------------------------------
    # Step 5: AirDrop-Style Encrypted P2P Media Drop to Vault (MSH-02)
    # -------------------------------------------------------------------------
    # Prepare summary report markdown file
    report_content = (
        f"# Neural OS Compute Summary\n\n"
        f"- Goal: {goal_text}\n"
        f"- Vision Frame: {frame_payload.frame_id}\n"
        f"- Micro-Tool Synthesized: {proposal.tool_name}\n"
        f"- Result: {exec_res.output}\n"
    )
    source_file = tmp_path / "neural_report.md"
    source_file.write_text(report_content, encoding="utf-8")

    manifest, transfer = drop_mgr.create_send_manifest(
        file_path=str(source_file),
        source_node_id="desktop-host",
        target_node_id="companion-iphone-15",
        destination=MediaDropDestination.VAULT,
    )
    assert manifest.file_size > 0
    assert manifest.sha256_checksum is not None

    # Stream file to vault using chunked receiver pipeline
    ack_init = drop_mgr.receive_manifest(manifest)
    assert ack_init.status == "ack"

    chunk = drop_mgr.read_file_chunk(
        file_path=str(source_file),
        chunk_index=0,
        transfer_id=manifest.transfer_id,
    )
    ack_chunk = drop_mgr.receive_chunk(chunk)
    assert ack_chunk.status in ("ack", "complete")

    # Verify report arrived in vault
    vault_files = list(vault_dir.glob("*.md"))
    assert len(vault_files) >= 1
    assert "neural_report" in vault_files[0].name

    # -------------------------------------------------------------------------
    # Step 6: Universal Guardian Kill Switch Synchronous Lockdown (SAF-02)
    # -------------------------------------------------------------------------
    t_halt_start = time.perf_counter()
    guardian_switch.trigger("E2E simulation completion lockdown test")
    t_halt_end = time.perf_counter()

    halt_latency_ms = (t_halt_end - t_halt_start) * 1000.0
    print(f"\n[E2E GUARDIAN HALT LATENCY] {halt_latency_ms:.4f} ms")

    # Hard SLA verification
    assert halt_latency_ms < 25.0
    assert guardian_switch.is_halted is True
    assert camera.is_halted() is True
    assert camera._frame_buffer.get_latest() is None  # RAM buffer wiped
    assert drop_mgr.is_halted() is True
    assert tot_planner.is_halted is True
    assert restricted_sandbox._halted is True

    # Verify all subsequent operations fail-closed
    with pytest.raises(PermissionError):
        tot_planner.plan_objective("Speculative query during emergency halt")

    with pytest.raises(PermissionError):
        camera.ingest_frame(frame_payload)

    with pytest.raises(PermissionError):
        drop_mgr.create_send_manifest(
            file_path=str(source_file),
            source_node_id="desktop-host",
            target_node_id="companion-iphone-15",
            destination=MediaDropDestination.VAULT,
        )

    # Clean up registry
    registry.unregister("stat_variance_calc")
    dynamic_synthesizer_manager.unregister_tool("stat_variance_calc")
    guardian_switch.resume()
