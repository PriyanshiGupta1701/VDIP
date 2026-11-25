const Navbar = () => {

    return (
        <nav className="flex items-center justify-center bg-white shadow-sm sticky top-0 z-20 md:h-[80px]">
            <div className="max-w-[1600px] w-full md:px-10 px-2.5 py-3 flex gap-10 justify-between items-center">
                <a href="/" className="flex flex-col justify-center outline-none" aria-label="VDIP - Vehicle Damage Intelligence Platform">
                    <span className="text-3xl md:text-4xl font-extrabold leading-none tracking-tight text-primary">VDIP</span>
                    <span className="mt-1 text-[10px] md:text-xs font-medium leading-none tracking-wide text-gray-500 uppercase">Vehicle Damage Intelligence Platform</span>
                </a>
            </div>
        </nav>
    )
}

export default Navbar
