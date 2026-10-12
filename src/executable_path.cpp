#include "opr2/executable_path.hpp"

#include <array>
#include <string>
#include <system_error>
#include <vector>

#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
#elif defined(__linux__)
#include <unistd.h>
#endif

namespace opr2 {

ExecutablePathResult executable_path() {
#if defined(_WIN32)
    std::vector<wchar_t> buffer(512);
    while (buffer.size() <= 32768) {
        const DWORD length = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
        if (length == 0) {
            return {{}, "cannot locate the running executable (Windows error " + std::to_string(GetLastError()) + ")"};
        }
        if (length < buffer.size() - 1) {
            return {std::filesystem::path(std::wstring(buffer.data(), length)), {}};
        }
        buffer.resize(buffer.size() * 2);
    }
    return {{}, "running executable path exceeds the supported Windows path length"};
#elif defined(__linux__)
    std::vector<char> buffer(512);
    while (buffer.size() <= 1024 * 1024) {
        const auto length = ::readlink("/proc/self/exe", buffer.data(), buffer.size());
        if (length < 0) {
            return {{}, "cannot locate the running executable through /proc/self/exe"};
        }
        if (static_cast<std::size_t>(length) < buffer.size()) {
            return {std::filesystem::path(std::string(buffer.data(), static_cast<std::size_t>(length))), {}};
        }
        buffer.resize(buffer.size() * 2);
    }
    return {{}, "running executable path exceeds the supported Linux path length"};
#else
    return {{}, "locating the running executable is unsupported on this platform"};
#endif
}

} // namespace opr2
