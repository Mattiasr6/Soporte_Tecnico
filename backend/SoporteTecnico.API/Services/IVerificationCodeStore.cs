namespace SoporteTecnico.API.Services;

public interface IVerificationCodeStore
{
    void Store(string email, string code);
    string? Get(string email);
    void Remove(string email);
}
