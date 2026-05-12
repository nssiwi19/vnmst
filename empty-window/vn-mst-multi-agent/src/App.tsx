import { useCallback, useMemo, useState } from "react";
import { ArchitectureFlow } from "./components/ArchitectureFlow";
import { runReportAgent, runResearchAgent, runVerificationAgent } from "./lib/agents";
import { buildCrmInsight } from "./lib/crm";
import { SAMPLE_COMPANIES } from "./lib/samples";
import { fetchBusinessByTaxCode, normalizeMst } from "./lib/vietqr";
import type { CrmPurpose, PipelineState } from "./types";

type TabId = "arch" | "pipeline" | "crm";

const initialPipeline = (mst: string): PipelineState => ({
  mst,
  raw: null,
  research: null,
  report: null,
  verification: null,
  step: "idle",
  error: null,
});

export default function App() {
  const [tab, setTab] = useState<TabId>("arch");
  const [mstInput, setMstInput] = useState("0100109106");
  const [purpose, setPurpose] = useState<CrmPurpose>("kyc");
  const [pipeline, setPipeline] = useState<PipelineState>(() => initialPipeline("0100109106"));

  const runPipeline = useCallback(async () => {
    const mst = normalizeMst(mstInput);
    setPipeline({
      mst,
      raw: null,
      research: null,
      report: null,
      verification: null,
      step: "fetching",
      error: null,
    });

    try {
      const raw = await fetchBusinessByTaxCode(mst);
      if (raw.code !== "00" || !raw.data) {
        setPipeline((p) => ({
          ...p,
          raw,
          step: "error",
          error: raw.desc || "MST không hợp lệ hoặc không có trong VietQR.",
        }));
        return;
      }

      setPipeline((p) => ({ ...p, raw, step: "research" }));
      const research = await runResearchAgent(raw.data);
      setPipeline((p) => ({ ...p, research, step: "report" }));

      const report = await runReportAgent(raw.data, research);
      setPipeline((p) => ({ ...p, report, step: "verification" }));

      const verification = await runVerificationAgent(raw.data, research);
      setPipeline({
        mst,
        raw,
        research,
        report,
        verification,
        step: "done",
        error: null,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Lỗi không xác định";
      setPipeline((p) => ({
        ...p,
        step: "error",
        error: msg,
      }));
    }
  }, [mstInput]);

  const crmFromPipeline = useMemo(() => {
    const inactive = pipeline.step === "error" || !pipeline.raw?.data;
    return buildCrmInsight(
      pipeline.raw?.data ?? null,
      pipeline.verification,
      purpose,
      inactive,
    );
  }, [pipeline.raw, pipeline.verification, pipeline.step, purpose]);

  const crmStandalone = useMemo(() => {
    const hasData = pipeline.raw?.code === "00" && pipeline.raw.data;
    return buildCrmInsight(
      hasData ? pipeline.raw!.data! : null,
      pipeline.verification,
      purpose,
      !hasData,
    );
  }, [pipeline.raw, pipeline.verification, purpose]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Hệ thống MST doanh nghiệp Việt Nam — Multi-Agent</h1>
        <p>
          Tra cứu qua VietQR, phân tích tuần tự ba agent (Research, Report, Verification), đồng bộ CRM
          theo mục đích nghiệp vụ.
        </p>
      </header>

      <nav className="tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "arch"}
          className={`tab${tab === "arch" ? " active" : ""}`}
          onClick={() => setTab("arch")}
        >
          Kiến trúc
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "pipeline"}
          className={`tab${tab === "pipeline" ? " active" : ""}`}
          onClick={() => setTab("pipeline")}
        >
          Multi-Agent Pipeline
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "crm"}
          className={`tab${tab === "crm" ? " active" : ""}`}
          onClick={() => setTab("crm")}
        >
          CRM Doanh nghiệp
        </button>
      </nav>

      {tab === "arch" && (
        <div>
          <div className="panel">
            <h2>Sơ đồ luồng</h2>
            <p className="muted">
              Từ MST nhập vào giao diện, hệ thống gọi VietQR để lấy dữ liệu định danh cơ bản, sau đó ba
              agent xử lý nối tiếp và ghi nhận vào CRM.
            </p>
            <ArchitectureFlow />
          </div>

          <div className="panel">
            <h2>Mô tả agent và nguồn dữ liệu</h2>
            <div className="agent-grid">
              <div className="agent-card">
                <strong>Research Agent</strong>
                Đọc JSON VietQR; suy luận hình thức pháp lý từ tên, gợi ý ngành và địa bàn từ địa chỉ
                và từ khóa. Output: bullet hồ sơ + metadata cấu trúc.
              </div>
              <div className="agent-card">
                <strong>Report Agent</strong>
                Tổng hợp báo cáo điều hành ngắn: tóm tắt định vị DN, khuyến nghị KYC/tín dụng, bảng
                thực thể chính (MST, tên, ngành, địa bàn).
              </div>
              <div className="agent-card">
                <strong>Verification Agent</strong>
                So khớp tên VI/EN, độ đầy đủ địa chỉ, quy tắc từ khóa rủi ro; tính trust score minh họa
                và danh sách cờ rủi ro có mức độ.
              </div>
            </div>
            <h3>Nguồn tích hợp</h3>
            <ul className="bullet-list">
              <li>
                <strong>VietQR</strong> —{" "}
                <code>GET https://api.vietqr.io/v2/business/{"{taxCode}"}</code> (dev: proxy{" "}
                <code>/vietqr-api</code>).
              </li>
              <li>
                <strong>Tổng cục Thuế</strong> — đối chiếu MST, trạng thái hoạt động, cơ quan thuế
                quản lý (nguồn chính thức).
              </li>
              <li>
                <strong>Cổng thông tin quốc gia về ĐKDN</strong> — bổ sung trạng thái pháp lý/hồ sơ đăng
                ký theo chính sách truy cập.
              </li>
              <li>
                <strong>Tra cứu hộ kinh doanh ngành Thuế</strong> — mở rộng độ phủ cá thể tại Hà Nội và
                TP.HCM.
              </li>
              <li>
                <strong>Heuristic nội bộ + CRM (tab 3)</strong> — suy luận ngành/pháp lý và gắn segment
                theo mục đích KYC, tín dụng, kiểm toán, hợp tác.
              </li>
            </ul>
          </div>

          <div className="panel">
            <h2>Thiết kế kho dữ liệu 100k bản ghi</h2>
            <ul className="bullet-list">
              <li>
                <strong>Quy mô:</strong> mục tiêu tối thiểu 100.000 bản ghi doanh nghiệp, ưu tiên địa bàn
                Hà Nội và TP.HCM.
              </li>
              <li>
                <strong>Chuẩn dữ liệu:</strong> MST, tên công ty, năm thành lập, SĐT, email, địa chỉ,
                ngành nghề kinh doanh.
              </li>
              <li>
                <strong>Xử lý hiệu năng:</strong> async workers, retry/backoff, tùy chọn proxy và
                user-agent rotation.
              </li>
              <li>
                <strong>Chất lượng:</strong> de-dup theo MST, chuẩn hóa định dạng địa chỉ và số điện thoại
                trước khi ghi kho.
              </li>
              <li>
                <strong>Storage:</strong> upsert trực tiếp lên Supabase (PostgreSQL) hoặc nạp batch lên
                BigQuery.
              </li>
            </ul>
          </div>
        </div>
      )}

      {tab === "pipeline" && (
        <div>
          <div className="panel">
            <h2>Chạy pipeline</h2>
            <p className="muted">
              Nhập MST hoặc chọn mẫu. Ứng dụng gọi VietQR (dữ liệu thật khi API khả dụng), rồi chạy ba
              agent tuần tự theo thứ tự Research → Report → Verification.
            </p>
            <div className="row">
              <div className="field">
                <label htmlFor="mst">Mã số thuế</label>
                <input
                  id="mst"
                  type="text"
                  value={mstInput}
                  onChange={(e) => setMstInput(e.target.value)}
                  placeholder="VD: 0100109106"
                />
              </div>
              <button
                type="button"
                className="btn"
                onClick={runPipeline}
                disabled={["fetching", "research", "report", "verification"].includes(
                  pipeline.step,
                )}
              >
                {["fetching", "research", "report", "verification"].includes(pipeline.step)
                  ? "Đang xử lý…"
                  : "Gọi VietQR & chạy agent"}
              </button>
            </div>
            <div className="chip-row">
              {SAMPLE_COMPANIES.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className="chip"
                  title={s.note}
                  onClick={() => setMstInput(s.mst)}
                >
                  {s.label.split("(")[0].trim()}
                </button>
              ))}
            </div>
            {pipeline.error && <div className="error-box">{pipeline.error}</div>}

            <h3>Tiến trình</h3>
            <ol className="step-list">
              <StepRow
                n={1}
                label="VietQR — tra cứu MST"
                state={
                  pipeline.step === "fetching"
                    ? "run"
                    : pipeline.raw
                      ? "done"
                      : "idle"
                }
              />
              <StepRow
                n={2}
                label="Agent Research"
                state={
                  pipeline.step === "research"
                    ? "run"
                    : pipeline.research
                      ? "done"
                      : "idle"
                }
              />
              <StepRow
                n={3}
                label="Agent Report"
                state={
                  pipeline.verification || pipeline.step === "done"
                    ? "done"
                    : pipeline.step === "report"
                      ? "run"
                      : "idle"
                }
              />
              <StepRow
                n={4}
                label="Agent Verification"
                state={
                  pipeline.verification
                    ? "done"
                    : pipeline.step === "verification"
                      ? "run"
                      : "idle"
                }
              />
            </ol>
          </div>

          {pipeline.raw?.data && (
            <div className="panel">
              <h2>Dữ liệu VietQR (raw)</h2>
              <pre className="code-block">{JSON.stringify(pipeline.raw, null, 2)}</pre>
            </div>
          )}

          {pipeline.research && (
            <div className="panel">
              <h2>Kết quả Research Agent</h2>
              <ul className="bullet-list">
                {pipeline.research.profileBullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <p className="muted">Nguồn: {pipeline.research.dataSources.join(" · ")}</p>
            </div>
          )}

          {pipeline.report && (
            <div className="panel">
              <h2>Báo cáo điều hành (Report Agent)</h2>
              <p>{pipeline.report.executiveSummary}</p>
              <h3>Khuyến nghị</h3>
              <ul className="bullet-list">
                {pipeline.report.recommendations.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              <h3>Thực thể chính</h3>
              <ul className="bullet-list">
                {pipeline.report.keyEntities.map((k) => (
                  <li key={k.label}>
                    <strong>{k.label}:</strong> {k.value}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {pipeline.verification && (
            <div className="panel">
              <h2>Verification Agent</h2>
              <p className="stat-inline">
                Trust score (minh họa): <strong>{pipeline.verification.trustScore}</strong> / 100
              </p>
              <h3>Cờ rủi ro</h3>
              {pipeline.verification.riskFlags.length === 0 ? (
                <p className="muted">Không phát hiện cờ theo quy tắc nội bộ.</p>
              ) : (
                <ul className="bullet-list">
                  {pipeline.verification.riskFlags.map((f) => (
                    <li key={f.message} className={`risk-${f.level === "high" ? "high" : f.level === "medium" ? "med" : "low"}`}>
                      [{f.level}] {f.message}
                    </li>
                  ))}
                </ul>
              )}
              <h3>Ghi chú tuân thủ</h3>
              <ul className="bullet-list">
                {pipeline.verification.complianceNotes.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="panel">
            <h2>Gợi ý CRM từ pipeline hiện tại</h2>
            <p>
              Segment:{" "}
              <span className={`segment-pill segment-${crmFromPipeline.segment}`}>
                {crmFromPipeline.segment}
              </span>
            </p>
            <ul className="bullet-list">
              {crmFromPipeline.rationale.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {tab === "crm" && (
        <div className="panel">
          <h2>Tra cứu CRM theo MST + mục đích</h2>
          <p className="muted">
            Dùng cùng MST đã nhập ở tab Pipeline. Chạy pipeline trước để có dữ liệu đầy đủ; nếu chưa
            chạy, hệ thống coi là Inactive.
          </p>
          <div className="row">
            <div className="field">
              <label htmlFor="purpose">Mục đích</label>
              <select
                id="purpose"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value as CrmPurpose)}
              >
                <option value="kyc">KYC / nhận diện khách hàng</option>
                <option value="credit">Tín dụng</option>
                <option value="audit">Kiểm toán</option>
                <option value="partnership">Thẩm định hợp tác</option>
              </select>
            </div>
            <div className="field">
              <label>MST hiện tại</label>
              <input type="text" value={normalizeMst(mstInput)} readOnly />
            </div>
          </div>

          <p style={{ marginTop: "1rem" }}>
            Phân loại AI (segment):{" "}
            <span className={`segment-pill segment-${crmStandalone.segment}`}>
              {crmStandalone.segment}
            </span>
          </p>

          <h3>Cơ sở & điều chỉnh theo mục đích</h3>
          <ul className="bullet-list">
            {crmStandalone.rationale.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="muted">
            Segment trả về gồm: Enterprise / SME / Startup / Risky / Inactive, được điều chỉnh theo mục
            đích nghiệp vụ đã chọn.
          </p>
          <h3>Điều chỉnh vận hành</h3>
          <ul className="bullet-list">
            {crmStandalone.purposeAdjustments.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <h3>Bước tiếp theo đề xuất</h3>
          <ul className="bullet-list">
            {crmStandalone.suggestedNextSteps.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function StepRow({
  n,
  label,
  state,
}: {
  n: number;
  label: string;
  state: "idle" | "run" | "done";
}) {
  return (
    <li>
      <span className={`step-badge${state === "done" ? " done" : ""}${state === "run" ? " run" : ""}`}>
        {state === "done" ? "OK" : n}
      </span>
      <span>{label}</span>
      {state === "run" && <span className="muted"> Đang chạy…</span>}
    </li>
  );
}
