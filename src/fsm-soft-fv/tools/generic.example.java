// Pseudo-Java, single file, structure-focused
// For guys like me thinks python code is a MESS, rather try prototype design in JAVA

import java.util.Map;
import java.util.HashMap;

/* ===============================
 * Result Envelope
 * Python: {"s","d","e","rb"}
 * =============================== */

class ToolError {
    public String code;
    public String msg;

    public ToolError(String code, String msg) {
        this.code = code;
        this.msg = msg;
    }
}

enum Status {
    OK,
    ERROR,
    RETRY
}

class ToolResult<T> {
    public Status s;   // status
    public T d;        // data
    public ToolError e;// error
    public String rb;  // rollback strategy

    public ToolResult(Status s, T d, ToolError e, String rb) {
        this.s = s;
        this.d = d;
        this.e = e;
        this.rb = rb;
    }
}


/* ===============================
 * BaseTool
 * Python: Tool
 * Template Method Pattern
 * =============================== */

abstract class BaseTool {

    protected String name = "base_tool";
    protected boolean retrySafe = true;

    protected <T> ToolResult<T> ok(T data) {
        return new ToolResult<>(Status.OK, data, null, "none");
    }

    protected <T> ToolResult<T> err(String code, String msg) {
        return new ToolResult<>(Status.ERROR, null, new ToolError(code, msg), "state");
    }

    protected <T> ToolResult<T> retry(String code, String msg) {
        return new ToolResult<>(Status.RETRY, null, new ToolError(code, msg), "state");
    }


    /* =========================================
     * FINAL entrypoint (Template Method)
     * Python: run()
     * ========================================= */

    public final ToolResult<?> run(Map<String, Object> args) {

        if (args == null) {
            return err("BAD_ARGS", "args must be an object");
        }

        try {
            Map<String, Object> normalized = validateArgs(args);
            return execute(normalized);

        } catch (IllegalArgumentException ex) {
            return err("BAD_ARGS", ex.getMessage());

        } catch (Exception ex) {
            return err("TOOL_FAIL", ex.getMessage());
        }
    }

    protected Map<String, Object> validateArgs(Map<String, Object> args) {
        return args;
    }

    // Must
    protected abstract ToolResult<?> execute(Map<String, Object> args);
}


/* ===============================
 * Example Tool
 * =============================== */

class ExampleTool extends BaseTool {

    public ExampleTool() {
        this.name = "example_tool";
    }

    @Override
    protected Map<String, Object> validateArgs(Map<String, Object> args) {

        String text = ((String) args.getOrDefault("text", "")).trim();

        if (text.isEmpty()) {
            throw new IllegalArgumentException("text is required");
        }

        Map<String, Object> normalized = new HashMap<>();
        normalized.put("text", text);
        return normalized;
    }

    @Override
    protected ToolResult<?> execute(Map<String, Object> args) {

        Map<String, Object> out = new HashMap<>();
        out.put("echo", args.get("text"));

        return ok(out);
    }
}


/* ===============================
 * Adapter for orchestrator
 * Python: def run(args): return ExampleTool().run(args)
 * =============================== */

public class ToolFramework {

    public static ToolResult<?> run(Map<String, Object> args) {
        return new ExampleTool().run(args);
    }
}
