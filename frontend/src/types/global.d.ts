type AttachedFile = {
    file: File;
    name: string;
    size: number;
    type: string;
}

type DetectionResponse = {
    status: string;
    session_id: string;
    result: {
       results: {
        dent: {
            bbox: [number, number, number, number] | null;
            severity: string | null;
            decision: string | null;
            confidence: number | null;
            depth: string | null;
        } | null;
        scratch: {
            bbox: [number, number, number, number] | null;
            severity: string | null;
            decision: string | null;
            confidence: number | null;
            length: string | null;
        } | null;
        crack: {
            bbox: [number, number, number, number] | null;
            severity: string | null;
            decision: string | null;
            confidence: number | null;
            length: string | null;
        } | null;
        rust: {
            bbox: [number, number, number, number] | null;
            severity: string | null;
            decision: string | null;
        } | null;
        glass_shatter: {
            bbox: [number, number, number, number] | null;
            decision: string | null;
            confidence: number | null;
        } | null;
        lamp_broken: {
            bbox: [number, number, number, number] | null;
            decision: string | null;
            confidence: number | null;
        } | null;
    };
    final_image: string; 
    };
    message: string;
}