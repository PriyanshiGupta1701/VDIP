import Navbar from "@/components/Navbar";
import { useState, type ReactNode, useEffect } from "react";
import ImageIcon from '@mui/icons-material/Image';
import SearchIcon from '@mui/icons-material/Search';
import StarIcon from '@mui/icons-material/Star';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import PlagiarismIcon from '@mui/icons-material/Plagiarism';
import BuildIcon from '@mui/icons-material/Build';
import EmailIcon from '@mui/icons-material/Email';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import BackupIcon from '@mui/icons-material/Backup';
import { API_BASE_URL } from '@/config';
import CircularProgress from "@mui/material/CircularProgress";
import { toast } from "react-toastify";

type DamageTypeData = {
    label: string;
    icon: ReactNode;
    desc: string;
}

type DamageTypes = {
    dent: DamageTypeData,
    scratch: DamageTypeData,
    crack: DamageTypeData,
    lamp_broken: DamageTypeData,
    glass_shatter: DamageTypeData,
    rust: DamageTypeData,
}

const DAMAGE_TYPES: DamageTypes = {
    dent: { label: "Dent", icon: <img src="/images/dent.svg" alt="Dent Icon" className="text-primary w-8 h-8 min-w-6 min-h-6 rounded-[5px]" />, desc: "Surface Deformation" },
    scratch: { label: "Scratch", icon: <img src="/images/scratch.svg" alt="Scratch Icon" className="text-primary w-8 h-8 min-w-6 min-h-6 rounded-[5px]" />, desc: "Paint Surface Damage" },
    crack: { label: "Crack", icon: <img src="/images/crack.svg" alt="crack Icon" className="text-primary w-8 h-8 min-w-6 min-h-6 rounded-[5px]" />, desc: "Structural Fracture" },
    lamp_broken: { label: "Broken Lamp", icon: <img src="/images/broken lamp.svg" alt="broken lamp Icon" className="text-primary w-8 h-8 min-w-6 min-h-6 rounded-[5px]" />, desc: "Light Fixture Damage" },
    glass_shatter: { label: "Glass Shatter", icon: <img src="/images/glass shatter.svg" alt="Glass Shatter Icon" className="text-primary w-8 h-8 min-w-6 min-h-6 rounded-[5px]" />, desc: "Windshield Break" },
    rust: { label: "Rust", icon: <img src="/images/rust.svg" alt="Rust Icon" className="text-primary w-8 h-8 min-w-6 min-h-6 rounded-[5px]" />, desc: "Surface Deformation" },
};

const SESSION_KEYS = {
    email: "user_email"
};

const Main = () => {
    const [file, setFile] = useState<File | null>(null);
    const [damageType, setDamageType] = useState<string>("");
    const [email, setEmail] = useState<string>("");
    const [isHome, setIsHome] = useState<boolean>(true);
    const [loading, setLoading] = useState<boolean>(false);
    const [emailLoading, setEmailLoading] = useState<boolean>(false);
    // state for API results
    const [detectionResults, setDetectionResults] = useState<DetectionResponse | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setDetectionResults(null);
            setIsHome(true);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (loading) return;
        setLoading(true);
        if (!file || !email) {
            toast.error("Please upload an image and enter your email.");
            setLoading(false);
            return;
        }
        const formData = new FormData();
        formData.append("file", file);
        formData.append("damage_type", damageType);
        formData.append("email_id", email);

        try {
            const response = await fetch(`${API_BASE_URL}/analyze-damage`, {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                throw new Error("Network response was not ok");
            } else if (response.status === 205) {
                toast.error(`No ${damageType} detected in the image. Please try with another image.`);
                setDetectionResults(null);
                setIsHome(true);
                setLoading(false);
                return;
            }

            const data: DetectionResponse = await response.json();
            setDetectionResults(data);
            setIsHome(false);
        } catch (error) {
            void error;
            console.error("Error during API call");
            toast.error("There was an error processing your request. Please try again.");
        }
        setLoading(false);
    };

    const sendEmail = async (e: React.FormEvent) => {
        e.preventDefault();
        if (emailLoading) return;
        if (!detectionResults) return;
        setEmailLoading(true);
        console.log("Sending email to:", email);
        try {
            const response = await fetch(`${API_BASE_URL}/email`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email: email }),
            });

            if (!response.ok) {
                throw new Error("Network response was not ok");
            }

            toast.success("Email sent successfully!");
        } catch (error) {
            void error;
            console.error("Error during API call");
            toast.error("There was an error processing your request. Please try again.");
        }
        setEmailLoading(false);
    };

    const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setEmail(e.target.value);
        sessionStorage.setItem(SESSION_KEYS.email, e.target.value);
    };

    useEffect(() => {
        const storedEmail = sessionStorage.getItem(SESSION_KEYS.email);
        if (storedEmail) {
            setEmail(storedEmail);
        }
    }, []);

    return (
        <>
            <Navbar />
            <div className="w-full min-h-[100vh-80px] h-full flex flex-col justify-start items-center bg-quaternary">
                <div className="flex flex-col w-full h-full md:px-10 md:py-10 max-w-[1600px] md:pt-10">
                    <div className='w-full flex flex-col justify-start items-center'>

                        <div className="flex md:flex-row gap-8 w-full">

                            <form onSubmit={handleSubmit} className="bg-background p-5 rounded-xl flex flex-col gap-6 min-w-[320px] h-full sticky top-28">
                                <div className="flex items-center justify-center gap-4">
                                    <FileUploadIcon className="text-primary" />
                                    <h2 className="text-[24px] font-semibold">
                                        Upload Image
                                    </h2>
                                </div>

                                <label className="border-2 border-dashed border-orange-300 rounded-xl flex flex-col md:gap-2 items-center justify-center p-4 text-center cursor-pointer">
                                    <input type="file" accept="image/png, image/jpeg, image/jpg, image/webp" className="hidden" onChange={handleFileChange} />
                                    <BackupIcon className="text-primary" fontSize="large" />
                                    <span className="text-[16px] text-secondary">
                                        Drag and drop your car image here
                                    </span>
                                    <span className="flex justify-center items-center md:gap-4 text-background rounded-[8px] bg-primary hover:bg-primary/90 text-[14px] font-extrabold px-4 py-3">
                                        Browse Files
                                    </span>
                                    <p className="text-[16px] text-secondary/50">PNG, JPG, JPEG, WEBP</p>
                                </label>

                                <div className="flex flex-col gap-3">
                                    <div className="flex items-center gap-2">
                                        <BuildIcon className="text-primary" />
                                        <label className="text-[20px]">
                                            Damage type (optional)
                                        </label>
                                    </div>
                                    <select
                                        title="damage-type"
                                        value={damageType}
                                        onChange={(e) => setDamageType(e.target.value)}
                                        className="w-full border rounded-lg px-3 py-2"
                                    >
                                        <option value="">Auto Detect</option>
                                        {
                                            Object.entries(DAMAGE_TYPES).map((d, index) => (
                                                <option key={index} value={d[0]}>{d[1].label}</option>
                                            ))
                                        }
                                    </select>
                                </div>

                                <div className="flex flex-col gap-3">
                                    <div className="flex items-center gap-2">
                                        <EmailIcon className="text-primary" />
                                        <label className="text-[20px]">
                                            Email<span className="text-red-500">*</span>
                                        </label>
                                    </div>
                                    <input
                                        type="email"
                                        required
                                        placeholder="your@email.com"
                                        value={email}
                                        onChange={handleEmailChange}
                                        className="w-full border rounded-lg px-3 py-2"
                                    />
                                </div>

                                <div className="flex flex-col w-full gap-4">
                                    <button
                                        type="submit"
                                        className="w-full flex justify-center items-center md:gap-4 text-background rounded-[8px] bg-primary hover:bg-primary/90 text-[16px] font-extrabold px-4 py-3 cursor-pointer h-12"
                                    >
                                        {
                                            loading ?
                                                <CircularProgress size={24} color="inherit" /> :
                                                <div className="flex w-full items-center md:gap-5">
                                                    <PlayArrowIcon />
                                                    <span className="w-full flex items-center">Run Detection</span>
                                                </div>
                                        }
                                    </button>
                                    {/* Footer Buttons */}

                                    <button disabled={detectionResults ? false : true} className="w-full flex justify-center items-center md:gap-4 text-background rounded-[8px] bg-primary hover:bg-primary/90 text-[16px] font-extrabold px-4 py-3 cursor-pointer h-12" onClick={sendEmail}>
                                        {emailLoading ? <CircularProgress size={24} color="inherit" /> : (<><EmailIcon /> <span className="w-full flex items-center">Send Report to Email</span></>)}
                                    </button>
                                </div>

                            </form>

                            <div className="w-full flex flex-col md:gap-8">
                                <div className="flex w-full gap-8">
                                    <div className="rounded-[10px] overflow-hidden h-[400px] bg-background flex flex-col w-full">
                                        {/* Header – don't let it stretch */}
                                        <div className="w-full flex gap-2 items-center shrink-0 bg-tertiary px-4 py-3">
                                            <ImageIcon />
                                            <h2 className="font-semibold text-lg text-secondary ml-2">
                                                Uploaded Image Preview
                                            </h2>
                                        </div>

                                        {/* Content area – allow it to shrink inside the 400px card */}
                                        <div className="flex-1 min-h-0 w-full">
                                            {file ? (
                                                <div className="h-full w-full flex justify-center items-center p-2 overflow-hidden">
                                                    <img
                                                        src={URL.createObjectURL(file)}
                                                        alt="Uploaded Preview"
                                                        className="max-h-full max-w-full object-contain rounded-lg"
                                                    />
                                                </div>
                                            ) : (
                                                <div className="h-full w-full flex flex-col justify-center items-center md:gap-1">
                                                    <DirectionsCarIcon className="!w-20 !h-20 text-secondary/30" />
                                                    <span className="font-medium text-[16px] text-secondary">No Image Uploaded</span>
                                                    <p className="text-secondary/50 font-medium text-[10px]">
                                                        Upload a car image to start detection
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="rounded-[10px] overflow-hidden h-[400px] flex flex-col items-center w-full bg-background">
                                        <div className="w-full flex items-center h-[52px] md:gap-4 bg-tertiary p-4">
                                            <SearchIcon />
                                            <h2 className="font-semibold text-lg mb-4 text-secondary">
                                                Detection Results
                                            </h2>
                                        </div>
                                        {
                                            loading ? (
                                                <div className="w-full h-full flex justify-center items-center p-2">
                                                    <CircularProgress size={36} color="inherit" className="text-tertiary" />
                                                </div>
                                            ) : detectionResults?.result.final_image ? (
                                                <div className="w-full h-full flex flex-1 justify-center items-center p-2">
                                                    <img
                                                        src={detectionResults?.result.final_image}
                                                        alt="Uploaded Preview"
                                                        className="rounded-lg max-h-full max-w-full object-contain"
                                                    />
                                                </div>
                                            ) : (
                                                <div className="w-full h-full flex flex-col justify-center items-center md:gap-1">
                                                    <PlagiarismIcon fontSize="inherit" className="!w-20 !h-20 text-secondary/30" />

                                                    <span className="font-medium text-[16px] text-secondary">No Damage Detected</span>
                                                    <p className="text-secondary/50 font-medium text-[10px]">
                                                        Use another image for detection
                                                    </p>
                                                </div>
                                            )
                                        }
                                    </div>
                                </div>

                                {
                                    isHome ? null : (
                                        <>
                                            <div className="w-full rounded-lg p-4 text-secondary/25 bg-background overflow-x-auto">
                                                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-secondary">
                                                    <img src="/images/summary.svg" alt="Summary Icon" className="text-primary" />
                                                    Detection Summary
                                                </h3>
                                                <div className="mt-3 w-full grid grid-cols-3 gap-3">
                                                    <DamageTypeBox item={DAMAGE_TYPES.dent} isEnabled={!!detectionResults?.result.results.dent} />
                                                    <DamageTypeBox item={DAMAGE_TYPES.scratch} isEnabled={!!detectionResults?.result.results.scratch} />
                                                    <DamageTypeBox item={DAMAGE_TYPES.crack} isEnabled={!!detectionResults?.result.results.crack} />
                                                    <DamageTypeBox item={DAMAGE_TYPES.lamp_broken} isEnabled={!!detectionResults?.result.results.lamp_broken} />
                                                    <DamageTypeBox item={DAMAGE_TYPES.glass_shatter} isEnabled={!!detectionResults?.result.results.glass_shatter} />
                                                    <DamageTypeBox item={DAMAGE_TYPES.rust} isEnabled={!!detectionResults?.result.results.rust} />
                                                </div>
                                            </div>
                                        
                                            <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6">
                                                {
                                                    detectionResults?.result.results.dent && (
                                                        <div className="border border-primary/40 bg-background rounded-lg p-4">
                                                            <div className="flex items-center gap-2 font-semibold mb-4 text-primary select-none">
                                                                {DAMAGE_TYPES.dent.icon}
                                                                <span>{DAMAGE_TYPES.dent.label}</span>
                                                            </div>
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Detected Bounding Box</span>
                                                                <span>
                                                                    {detectionResults.result.results.dent.bbox
                                                                        ? `[${detectionResults.result.results.dent.bbox.join(',')}]`
                                                                        : ""}
                                                                </span>
                                                            </div>
                                                            <hr className="text-secondary/10" />
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Depth</span>
                                                                <span>{detectionResults.result.results.dent.depth}</span>
                                                            </div>
                                                            <hr className="text-secondary/10" />
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Severity</span>
                                                                <span>{detectionResults.result.results.dent.severity}</span>
                                                            </div>
                                                        </div>
                                                    )
                                                }

                                                {
                                                    detectionResults?.result.results.scratch && (
                                                        <div className="border border-primary/40 bg-background rounded-lg p-4">
                                                            <div className="flex items-center gap-2 font-semibold mb-4 text-primary select-none">
                                                                {DAMAGE_TYPES.scratch.icon}
                                                                <span>{DAMAGE_TYPES.scratch.label}</span>
                                                            </div>
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Detected Bounding Box</span>
                                                                <span>
                                                                    {detectionResults.result.results.scratch.bbox
                                                                        ? `[${detectionResults.result.results.scratch.bbox.join(',')}]`
                                                                        : ""}
                                                                </span>
                                                            </div>
                                                            <hr className="text-secondary/10" />
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Length</span>
                                                                <span>{detectionResults.result.results.scratch.length}</span>
                                                            </div>
                                                            <hr className="text-secondary/10" />
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Severity</span>
                                                                <span>{detectionResults.result.results.scratch.severity}</span>
                                                            </div>
                                                        </div>
                                                    )
                                                }

                                                {
                                                    detectionResults?.result.results.crack && (
                                                        <div className="border border-primary/40 bg-background rounded-lg p-4">
                                                            <div className="flex items-center gap-2 font-semibold mb-4 text-primary select-none">
                                                                {DAMAGE_TYPES.crack.icon}
                                                                <span>{DAMAGE_TYPES.crack.label}</span>
                                                            </div>
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Detected Bounding Box</span>
                                                                <span>
                                                                    {detectionResults.result.results.crack.bbox
                                                                        ? `[${detectionResults.result.results.crack.bbox.join(',')}]`
                                                                        : ""}
                                                                </span>
                                                            </div>
                                                            <hr className="text-secondary/10" />
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Length</span>
                                                                <span>{detectionResults.result.results.crack.length}</span>
                                                            </div>
                                                            <hr className="text-secondary/10" />
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Severity</span>
                                                                <span>{detectionResults.result.results.crack.severity}</span>
                                                            </div>
                                                        </div>
                                                    )
                                                }

                                                {
                                                    detectionResults?.result.results.lamp_broken && (
                                                        <div className="border border-primary/40 bg-background rounded-lg p-4">
                                                            <div className="flex items-center gap-2 font-semibold mb-4 text-primary select-none">
                                                                {DAMAGE_TYPES.lamp_broken.icon}
                                                                <span>{DAMAGE_TYPES.lamp_broken.label}</span>
                                                            </div>
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Detected Bounding Box</span>
                                                                <span>
                                                                    {detectionResults.result.results.lamp_broken.bbox
                                                                        ? `[${detectionResults.result.results.lamp_broken.bbox.join(',')}]`
                                                                        : ""}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    )
                                                }

                                                {
                                                    detectionResults?.result.results.glass_shatter && (
                                                        <div className="border border-primary/40 bg-background rounded-lg p-4">
                                                            <div className="flex items-center gap-2 font-semibold mb-4 text-primary select-none">
                                                                {DAMAGE_TYPES.glass_shatter.icon}
                                                                <span>{DAMAGE_TYPES.glass_shatter.label}</span>
                                                            </div>
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Detected Bounding Box</span>
                                                                <span>
                                                                    {detectionResults.result.results.glass_shatter.bbox
                                                                        ? `[${detectionResults.result.results.glass_shatter.bbox.join(',')}]`
                                                                        : ""}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    )
                                                }

                                                {
                                                    detectionResults?.result.results.rust && (
                                                        <div className="border border-primary/40 bg-background rounded-lg p-4">
                                                            <div className="flex items-center gap-2 font-semibold mb-4 text-primary select-none">
                                                                {DAMAGE_TYPES.rust.icon}
                                                                <span>{DAMAGE_TYPES.rust.label}</span>
                                                            </div>
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Detected Bounding Box</span>
                                                                <span>
                                                                    {detectionResults.result.results.rust.bbox
                                                                        ? `[${detectionResults.result.results.rust.bbox.join(',')}]`
                                                                        : ""}
                                                                </span>
                                                            </div>
                                                            <hr className="text-secondary/10" />
                                                            <div className="flex justify-between items-center text-secondary mb-2 text-sm">
                                                                <span>Severity</span>
                                                                <span>{detectionResults.result.results.rust.severity}</span>
                                                            </div>
                                                        </div>
                                                    )
                                                }
                                            </div>
                                        </>

                                    )
                                }

                                <div className="bg-background px-6 py-6 rounded-xl w-full">
                                    <div className="text-xl font-semibold mb-4 flex items-center gap-2">
                                        <StarIcon className="text-primary" color="inherit" />
                                        <h2 className="font-medium text-[24px]">Key Features</h2>
                                    </div>
                                    <div className="flex flex-col md:flex-row gap-6 justify-between md:py-10 md:px-8">
                                        <div className="text-center w-full max-w-[200px] flex flex-col justify-start items-center gap-1.5">
                                            <div className="bg-accent text-primary flex justify-center items-center p-1.5 w-10 h-10 rounded-[5px]"><SearchIcon className="text-primary" /></div>
                                            <h3 className="font-semibold text-[16px]">Multi-Class Damage Detection</h3>
                                            <p className="text-[12px] font-light">
                                                Identifies multiple car surface damages accurately.
                                            </p>
                                        </div>
                                        <div className="text-center w-full max-w-[200px] flex flex-col justify-start items-center gap-1.5">
                                            <div className="bg-accent text-primary flex justify-center items-center p-1.5 w-10 h-10 rounded-[5px]"><img title="severity" src="/images/severity.svg" /></div>
                                            <h3 className="font-semibold text-[16px]">Damage-Specific Severity Estimation</h3>
                                            <p className="text-[12px] font-light">
                                                Estimates severity using tailored models including dept, length, severity.
                                            </p>
                                        </div>
                                        <div className="text-center w-full max-w-[200px] flex flex-col justify-start items-center gap-1.5">
                                            <div className="bg-accent text-primary flex justify-center items-center p-1.5 w-10 h-10 rounded-[5px]"><img title="output" src="/images/ai_detection_output.svg" className="text-primary font-medium" /></div>
                                            <h3 className="font-semibold text-[16px]">AI-Powered Damage Resolution Guidance</h3>
                                            <p className="text-[12px] font-light">
                                                Provides automated repair instructions and part replacement suggestions
                                            </p>
                                        </div>
                                    </div>
                                </div>


                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

const DamageTypeBox = ({ item, isEnabled }: { item: DamageTypeData; isEnabled: boolean }) => {
    return (
        <div className={`w-full text-secondary/30 flex items-center gap-2 border rounded-md px-3 py-2 whitespace-nowrap ${isEnabled ? "" : "opacity-60 pointer-events-none"}`}
        >
            <div>{item.icon}</div>
            <div className="text-md text-secondary font-semibold">
                {item.label}
                <div className="text-[12px] font-semibold text-secondary/50">{item.desc}</div>
            </div>
        </div>
    )
}

export default Main;