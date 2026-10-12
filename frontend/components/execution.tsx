import { Panel, Empty } from "./ui";
export type PaperFill = {
  id: string;
  ticker: string;
  quantity: string;
  price: string;
  fee: string;
  side: string;
  observation_time: string;
  fill_time: string;
  provider: string;
  label: string;
};
export default function Execution({ fills }: { fills: PaperFill[] }) {
  return (
    <Panel
      title="Paper execution record"
      aside={<span className="badge paper">PAPER / SIMULATED</span>}
    >
      {fills.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Fractional shares</th>
                <th>Fill price (USD)</th>
                <th>Fee (USD)</th>
                <th>Supported observation (UTC)</th>
              </tr>
            </thead>
            <tbody>
              {fills.map((f) => (
                <tr key={f.id}>
                  <td>{f.ticker}</td>
                  <td>{f.side}</td>
                  <td>{Number(f.quantity).toFixed(8)}</td>
                  <td>{Number(f.price).toFixed(6)}</td>
                  <td>{Number(f.fee).toFixed(2)}</td>
                  <td>
                    {f.observation_time.replace("T", " ").replace("+00:00", "")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty text="No paper fills recorded in this cycle." />
      )}
      <p className="subtle">
        Deterministic spread/slippage/fees. Prices are observations, not live
        quotes. Unsupported exits remain open until recovery.
      </p>
    </Panel>
  );
}
